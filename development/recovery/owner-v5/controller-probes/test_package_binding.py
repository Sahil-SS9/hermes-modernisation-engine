#!/usr/bin/env python3
"""Controller-owned approval-package tests. Throwaway in-memory keys only.

No owner private key, authority claim, Docker operation or project execution.
The phase signatures use the actual PUBLIC request bytes with a throwaway key;
the public-key seam is replaced solely for these isolated verification tests.
"""

import base64
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
ORIGINAL = ROOT / 'requests/trial-v5-1792372144283845183'
SPEC = importlib.util.spec_from_file_location('controller_package_target', ROOT / 'run-trial-v5.py')
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_payload(root, approval, manifest):
    """Independent format oracle; must agree with the Bash signer and verifier."""
    fields = [
        ('manifest_sha256', sha(approval / 'manifest.json')),
        ('runner_sha256', sha(root / 'run-trial-v5.py')),
        ('preparer_sha256', sha(root / 'prepare-trial-v5.py')),
        ('expectation_sha256', sha(Path(manifest['execution']['expectation_file']))),
        ('signer_sha256', sha(root / 'sign-owner-trial-v5.sh')),
        ('baseline_request_sha256', sha(approval / 'baseline.request.json')),
        ('candidate_request_sha256', sha(approval / 'candidate.request.json')),
        ('expires_at_epoch', str(manifest['grant']['expires_at_epoch'])),
    ]
    return ('trial-v5-package-v1\n' + ''.join(f'{key}={value}\n' for key, value in fields)).encode()


class PackageBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='controller-v5-binding-', dir=os.environ['TMPDIR'])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.approval = self.root / 'requests'
        self.approval.mkdir()
        for name in ('run-trial-v5.py', 'prepare-trial-v5.py', 'sign-owner-trial-v5.sh', 'EXPECTED-CASES-V4.json'):
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        for phase in ('baseline', 'candidate'):
            (self.approval / f'{phase}.request.json').write_bytes((ORIGINAL / f'{phase}.request.json').read_bytes())
        self.manifest = copy.deepcopy(json.loads((ORIGINAL / 'manifest.json').read_bytes()))
        self.manifest['runner'] = {'path': str(self.root / 'run-trial-v5.py'), 'sha256': sha(self.root / 'run-trial-v5.py')}
        self.manifest['preparer'] = {'path': str(self.root / 'prepare-trial-v5.py'), 'sha256': sha(self.root / 'prepare-trial-v5.py')}
        self.manifest['signing_script'] = {'path': str(self.root / 'sign-owner-trial-v5.sh')}
        self.manifest['execution']['expectation_file'] = str(self.root / 'EXPECTED-CASES-V4.json')
        self.write_manifest()
        self.manifest['_approval_dir'] = str(self.approval)
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.payload = expected_payload(self.root, self.approval, self.manifest)
        self.values = {
            'manifest_sha256': sha(self.approval / 'manifest.json'),
            'runner_sha256': sha(self.root / 'run-trial-v5.py'),
            'expires_at_epoch': str(self.manifest['grant']['expires_at_epoch']),
            'package_payload_base64': base64.b64encode(self.payload).decode(),
            'package_signature_base64': base64.b64encode(self.key.sign(self.payload)).decode(),
        }
        for phase in ('baseline', 'candidate'):
            self.values[phase] = base64.b64encode(self.key.sign((self.approval / f'{phase}.request.json').read_bytes())).decode()
        self.signatures = self.root / 'fixture-signatures.txt'

    def write_manifest(self):
        body = {key: value for key, value in self.manifest.items() if not key.startswith('_')}
        (self.approval / 'manifest.json').write_text(json.dumps(body, sort_keys=True, separators=(',', ':')))

    def verify(self):
        self.signatures.write_text('trial-v5 signatures\n' + ''.join(f'{key}={value}\n' for key, value in self.values.items()))
        with patch.object(TARGET, 'TRIAL_ROOT', self.root), patch.object(TARGET.prep, '_enrolled_public', return_value=self.public):
            return TARGET._signatures(self.signatures, self.manifest, sha(self.approval / 'manifest.json'))

    def test_valid_package_and_both_phase_signatures_are_accepted(self):
        self.assertEqual(set(self.verify()), {'baseline', 'candidate'})

    def test_missing_package_attestation_is_refused(self):
        self.values.pop('package_signature_base64')
        self.values.pop('package_payload_base64')
        with self.assertRaises(TARGET.TrialError):
            self.verify()

    def test_wrong_package_signer_is_refused_before_any_claim(self):
        wrong = Ed25519PrivateKey.generate()
        self.values['package_signature_base64'] = base64.b64encode(wrong.sign(self.payload)).decode()
        with self.assertRaises(TARGET.TrialError):
            self.verify()

    def test_ledger_redirect_and_unsigned_metadata_retag_are_refused(self):
        self.manifest['execution']['ledger'] = str(self.root / 'redirected-claims.sqlite')
        self.write_manifest()
        self.values['manifest_sha256'] = sha(self.approval / 'manifest.json')
        with self.assertRaises(TARGET.TrialError):
            self.verify()
        self.assertFalse((self.root / 'redirected-claims.sqlite').exists())

    def test_runner_edit_and_unsigned_hash_retag_are_refused(self):
        path = self.root / 'run-trial-v5.py'
        path.write_bytes(path.read_bytes() + b'\n# post-signature mutation\n')
        self.values['runner_sha256'] = sha(path)
        with self.assertRaises(TARGET.TrialError):
            self.verify()

    def test_preparer_edit_is_refused(self):
        path = self.root / 'prepare-trial-v5.py'
        path.write_bytes(path.read_bytes() + b'\n# post-signature mutation\n')
        with self.assertRaises(TARGET.TrialError):
            self.verify()

    def test_expectation_edit_is_refused(self):
        path = self.root / 'EXPECTED-CASES-V4.json'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaises(TARGET.TrialError):
            self.verify()

    def test_invalid_candidate_signature_is_refused_before_baseline_use(self):
        wrong = Ed25519PrivateKey.generate()
        body = (self.approval / 'candidate.request.json').read_bytes()
        self.values['candidate'] = base64.b64encode(wrong.sign(body)).decode()
        with self.assertRaises(TARGET.TrialError):
            self.verify()


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PackageBindingTests))
    evidence = ROOT / 'controller-evidence'
    evidence.mkdir(exist_ok=True)
    receipt = evidence / f'package-binding-{time.time_ns()}.json'
    receipt.write_text(json.dumps({
        'scope': 'approval verification with throwaway keys; zero authority claims or execution',
        'runner_sha256': sha(ROOT / 'run-trial-v5.py'),
        'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'failed_tests': [str(test) for test, _ in result.failures],
    }, sort_keys=True, indent=2) + '\n')
    print('CONTROLLER_RECEIPT', receipt)
    raise SystemExit(0 if result.wasSuccessful() else 1)

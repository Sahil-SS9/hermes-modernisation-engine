#!/usr/bin/env python3
"""Exercise the ACTUAL generated signer with throwaway keys and scratch outputs.

Only the enrolled PEM, agent-user guard and signature destination are changed in
positive variants. All real request bytes and pinned input files stay unchanged.
No owner private key is read. No grant is claimed and no project code is run.
"""

import base64
import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
STATE = json.loads((ROOT / 'ACTIVE-PACKAGE.json').read_bytes())
APPROVAL = Path(STATE['approval_directory'])
SPEC = importlib.util.spec_from_file_location('controller_signer_verifier', ROOT / 'run-trial-v5.py')
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)
SOURCE = (ROOT / 'sign-owner-trial-v5.sh').read_text()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ActualSignerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='controller-v5-signer-', dir=os.environ['TMPDIR'])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tmp = self.root / 'tmp'
        self.tmp.mkdir()
        self.sign_dir = self.root / 'signatures'
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.pem = self.key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode().strip()
        self.key_path = self.root / 'fixture-only.key'
        self.key_path.write_bytes(self.key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        self.key_path.chmod(0o600)
        self.assertFalse(TARGET.prep.LEDGER.exists(), 'a real claim file must not exist during signing tests')

    def tearDown(self):
        self.assertFalse(TARGET.prep.LEDGER.exists(), 'signing test created a real authority claim file')
        self.assertFalse(Path(TARGET.DEFAULT_SIGNATURES).exists(), 'signing test wrote into the owner account')

    def variant(self, extra=None):
        text, count = re.subn(r"ENROLLED_PEM='[^']*'", lambda _: "ENROLLED_PEM='" + self.pem + "'", SOURCE, count=1)
        self.assertEqual(count, 1)
        fields = {'AGENT_USER': 'controller-fixture-agent', 'SIGN_DIR': str(self.sign_dir)}
        fields.update(extra or {})
        for key, value in fields.items():
            pattern = rf'^{re.escape(key)}=.*$'
            text, count = re.subn(pattern, lambda _: f'{key}="{value}"', text, count=1, flags=re.M)
            self.assertEqual(count, 1, key)
        # These are the real embedded run requests, not toy substitutes.
        self.assertEqual(re.search(r'^REQUEST_B64=.*$', text, re.M).group(), re.search(r'^REQUEST_B64=.*$', SOURCE, re.M).group())
        script = self.root / 'sign-variant.sh'
        script.write_text(text)
        return script

    def run_signer(self, script, answer='YES', key=None, path=None):
        return subprocess.run(
            ['bash', str(script)], input=f'{answer}\n{key or self.key_path}\n',
            capture_output=True, text=True, timeout=45,
            env={'HOME': str(self.root), 'TMPDIR': str(self.tmp), 'PATH': path or '/usr/bin:/bin'},
        )

    def assert_clean_refusal(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('REFUSED:', result.stderr)
        self.assertFalse((self.sign_dir / 'trial-v5-signatures.txt').exists())
        self.assertEqual(list(self.tmp.glob('trial-v5-sign.*')), [])

    def signed_variant(self):
        script = self.variant()
        result = self.run_signer(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        signature_file = self.sign_dir / 'trial-v5-signatures.txt'
        self.assertTrue(signature_file.is_file())
        values = dict(line.split('=', 1) for line in signature_file.read_text().splitlines()[1:])
        for phase in ('baseline', 'candidate'):
            self.key.public_key().verify(base64.b64decode(values[phase], validate=True), (APPROVAL / f'{phase}.request.json').read_bytes())
        payload = base64.b64decode(values['package_payload_base64'], validate=True)
        self.key.public_key().verify(base64.b64decode(values['package_signature_base64'], validate=True), payload)
        shadow = self.root / 'verifier-inputs'
        shadow.mkdir()
        for filename in ('run-trial-v5.py', 'prepare-trial-v5.py'):
            (shadow / filename).write_bytes((ROOT / filename).read_bytes())
        (shadow / 'sign-owner-trial-v5.sh').write_bytes(script.read_bytes())
        manifest = copy.deepcopy(json.loads((APPROVAL / 'manifest.json').read_bytes()))
        manifest['_approval_dir'] = str(APPROVAL)
        with patch.object(TARGET, 'TRIAL_ROOT', shadow), patch.object(TARGET.prep, '_enrolled_public', return_value=self.public):
            checked = TARGET._signatures(signature_file, manifest, sha(APPROVAL / 'manifest.json'))
        self.assertEqual(set(checked), {'baseline', 'candidate'})
        self.assertEqual(list(self.tmp.glob('trial-v5-sign.*')), [])
        self.assertEqual(signature_file.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.sign_dir.stat().st_mode & 0o777, 0o755)
        return signature_file

    def test_actual_request_bytes_sign_and_verify_end_to_end(self):
        self.signed_variant()

    def test_wrong_private_key_refused(self):
        wrong = self.root / 'wrong-fixture.key'
        wrong.write_bytes(Ed25519PrivateKey.generate().private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        wrong.chmod(0o600)
        self.assert_clean_refusal(self.run_signer(self.variant(), key=wrong))

    def test_declined_confirmation_writes_no_signatures(self):
        self.assert_clean_refusal(self.run_signer(self.variant(), answer='NO'))

    def test_expired_variant_refused(self):
        self.assert_clean_refusal(self.run_signer(self.variant({'EXPIRES_EPOCH': '0'})))

    def test_actual_signer_refuses_agent_account(self):
        self.assert_clean_refusal(self.run_signer(ROOT / 'sign-owner-trial-v5.sh'))

    def test_root_guard_refused_with_simulated_id(self):
        # This checks the guard, not a claim that the test acquired root.
        fake_bin = self.root / 'bin'
        fake_bin.mkdir()
        fake_id = fake_bin / 'id'
        fake_id.write_text('#!/bin/sh\nif [ "$1" = "-u" ]; then printf "0\\n"; else printf "root\\n"; fi\n')
        fake_id.chmod(0o755)
        self.assert_clean_refusal(self.run_signer(self.variant(), path=str(fake_bin) + ':/usr/bin:/bin'))

    def test_changed_runner_file_refused_before_key_use(self):
        changed = self.root / 'changed-runner.py'
        changed.write_bytes((ROOT / 'run-trial-v5.py').read_bytes() + b'\n# changed\n')
        self.assert_clean_refusal(self.run_signer(self.variant({'RUNNER_PATH': str(changed)})))

    def test_existing_signature_not_overwritten(self):
        self.sign_dir.mkdir()
        output = self.sign_dir / 'trial-v5-signatures.txt'
        output.write_text('existing-signature-sentinel')
        result = self.run_signer(self.variant())
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(), 'existing-signature-sentinel')

    def test_dangling_signature_symlink_refused(self):
        self.sign_dir.mkdir()
        output = self.sign_dir / 'trial-v5-signatures.txt'
        absent = self.root / 'must-not-be-created'
        output.symlink_to(absent)
        result = self.run_signer(self.variant())
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(absent.exists())
        self.assertTrue(output.is_symlink())

    def test_unenrolled_fixture_package_cannot_start_real_runner(self):
        signatures = self.signed_variant()
        result = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'run-trial-v5.py'), str(APPROVAL), '--signatures', str(signatures)],
            capture_output=True, text=True, timeout=45,
        )
        self.assertNotEqual(result.returncode, 0)
        refused = json.loads(result.stderr)
        self.assertEqual(refused['status'], 'REFUSED')
        self.assertFalse(TARGET.prep.LEDGER.exists())


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActualSignerTests))
    receipt = ROOT / 'controller-evidence' / f'actual-signer-{time.time_ns()}.json'
    receipt.write_text(json.dumps({
        'scope': 'actual generated signer, throwaway keys, real request bytes; no owner key or grant consumption',
        'active_manifest_sha256': sha(APPROVAL / 'manifest.json'),
        'runner_sha256': sha(ROOT / 'run-trial-v5.py'), 'signer_sha256': sha(ROOT / 'sign-owner-trial-v5.sh'),
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'real_claim_ledger_exists': TARGET.prep.LEDGER.exists(),
        'owner_signature_file_exists': Path(TARGET.DEFAULT_SIGNATURES).exists(),
        'failed_tests': [str(test) for test, _ in result.failures + result.errors],
    }, sort_keys=True, indent=2) + '\n')
    print('CONTROLLER_RECEIPT', receipt)
    raise SystemExit(0 if result.wasSuccessful() else 1)

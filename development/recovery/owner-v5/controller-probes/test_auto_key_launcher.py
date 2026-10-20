#!/usr/bin/env python3
"""Private-key lookup launcher tests: synthetic keys in NEW private scratch only.

No owner key is accessed, changed or generated. The real signer is copied for
fixtures; only its public identity, agent guard and signature destination change.
Actual public request bytes and their pins stay unchanged. No project run.
"""

import argparse
import base64
import getpass
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

CONTROL = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
LAUNCHER = Path('/home/kensei/handoff/agent-plugin-plans/approvals/sign-modernisation-v5-auto.sh')
ORIGINAL = CONTROL / 'sign-owner-trial-v5.sh'
STATE = json.loads((CONTROL / 'ACTIVE-PACKAGE.json').read_bytes())
APPROVAL = Path(STATE['approval_directory'])
parser = argparse.ArgumentParser()
parser.add_argument('--before', action='store_true')
ARGS = parser.parse_args()


def replace_field(text, name, value):
    text, count = re.subn(rf'^{re.escape(name)}=.*$', lambda _: f'{name}="{value}"', text, count=1, flags=re.M)
    assert count == 1, name
    return text


def replace_pem(text, pem):
    text, count = re.subn(r"ENROLLED_PEM='[^']*'", lambda _: "ENROLLED_PEM='" + pem + "'", text, count=1)
    assert count == 1
    return text


class AutoKeyLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='controller-v5-auto-key-', dir=os.environ['TMPDIR'])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.tmp = self.root / 'tmp'
        self.tmp.mkdir()
        self.key = Ed25519PrivateKey.generate()
        self.pem = self.key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode().strip()
        folder = self.home / 'modernisation-owner.fixture'
        folder.mkdir(mode=0o700)
        self.key_path = folder / 'owner.key'
        self.key_path.write_bytes(self.key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        self.key_path.chmod(0o600)
        self.key_digest = hashlib.sha256(self.key_path.read_bytes()).hexdigest()
        self.output = self.home / 'signatures' / 'trial-v5-signatures.txt'
        text = replace_pem(ORIGINAL.read_text(), self.pem)
        text = replace_field(text, 'AGENT_USER', 'fixture-not-the-actual-agent')
        text = replace_field(text, 'SIGN_DIR', str(self.output.parent))
        self.signer = self.root / 'fixture-signer.sh'
        self.signer.write_text(text)
        self.signer_sha = hashlib.sha256(self.signer.read_bytes()).hexdigest()

    def launcher(self):
        if ARGS.before:
            return self.signer
        text = replace_pem(LAUNCHER.read_text(), self.pem)
        for name, value in [('OWNER_USER', getpass.getuser()), ('SIGNER', str(self.signer)), ('SIGNER_SHA', self.signer_sha)]:
            text = replace_field(text, name, value)
        result = self.root / 'fixture-launcher.sh'
        result.write_text(text)
        return result

    def run_launcher(self, answer='YES', script=None):
        return subprocess.run(
            ['bash', str(script or self.launcher())], input=answer + '\n\n',
            text=True, capture_output=True, timeout=45,
            env={'HOME': str(self.home), 'TMPDIR': str(self.tmp), 'PATH': '/usr/bin:/bin'},
        )

    def assert_no_signature(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.home.glob('.modernisation-v5-help.*')), [])

    def test_registered_private_folder_key_is_found_without_manual_path(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.output.is_file())
        values = dict(line.split('=', 1) for line in self.output.read_text().splitlines()[1:])
        for phase in ('baseline', 'candidate'):
            self.key.public_key().verify(base64.b64decode(values[phase], validate=True), (APPROVAL / f'{phase}.request.json').read_bytes())
        payload = base64.b64decode(values['package_payload_base64'], validate=True)
        self.key.public_key().verify(base64.b64decode(values['package_signature_base64'], validate=True), payload)
        self.assertEqual(hashlib.sha256(self.key_path.read_bytes()).hexdigest(), self.key_digest)
        self.assertNotIn('BEGIN PRIVATE KEY', result.stdout + result.stderr)
        self.assertEqual(list(self.home.glob('.modernisation-v5-help.*')), [])

    def test_wrong_key_is_not_selected_or_replaced(self):
        self.key_path.write_bytes(Ed25519PrivateKey.generate().private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        before = self.key_path.read_bytes()
        self.assert_no_signature(self.run_launcher())
        self.assertEqual(self.key_path.read_bytes(), before)

    def test_decline_does_not_sign(self):
        self.assert_no_signature(self.run_launcher(answer='NO'))

    def test_symlinked_key_is_not_followed(self):
        original = self.home / 'actual-fixture.key'
        self.key_path.rename(original)
        self.key_path.symlink_to(original)
        self.assert_no_signature(self.run_launcher())

    def test_changed_signer_refused(self):
        script = self.launcher()
        self.signer.write_bytes(self.signer.read_bytes() + b'\n# changed after pinning\n')
        self.assert_no_signature(self.run_launcher(script=script))

    def test_no_auto_yes_or_key_override_in_real_agent_account(self):
        self.assert_no_signature(self.run_launcher(script=LAUNCHER))


if __name__ == '__main__':
    suite = (unittest.TestSuite([AutoKeyLauncherTests('test_registered_private_folder_key_is_found_without_manual_path')])
             if ARGS.before else unittest.defaultTestLoader.loadTestsFromTestCase(AutoKeyLauncherTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = CONTROL / 'controller-evidence' / f'auto-key-launcher-{time.time_ns()}.json'
    receipt.write_text(json.dumps({
        'scope': 'registered-key discovery and delegation to unchanged signer; throwaway fixture keys only',
        'before': ARGS.before, 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'signer_source_sha256': hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        'real_owner_key_accessed': False, 'real_project_execution': False,
    }, sort_keys=True, indent=2) + '\n')
    print('CONTROLLER_RECEIPT', receipt)
    raise SystemExit(0 if result.wasSuccessful() else 1)

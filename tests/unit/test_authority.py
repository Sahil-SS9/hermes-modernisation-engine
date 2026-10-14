"""Ephemeral evaluator keys prove verification mechanics, not real owner enrolment."""
import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hermes_modernisation.approvals import AuthorityDenied, ExternalAuthority


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.ledger = Path(self.temp.name)/'grants.sqlite'
        self.auth = ExternalAuthority({'owner-test': public}, self.ledger, clock=lambda: 100)
        self.operation = {'schema_version': 1, 'job_id': 'job-test', 'attempt_id': 'attempt-1', 'actor': 'owner-test', 'profile': 'test', 'source_digest': 'a'*64, 'candidate_digest': 'b'*64, 'oracle_digest': 'c'*64, 'environment_digest': 'd'*64, 'image_digest': 'e'*64, 'argv': ['python', '-m', 'unittest'], 'read_roots': ['/source'], 'write_roots': ['/tmp', '/work'], 'network': 'none', 'timeout_seconds': 30, 'output_limit_bytes': 1048576}

    def grant(self, **changes):
        body = {'schema_version': 1, 'operation': copy.deepcopy(self.operation), 'nonce': 'nonce-000001', 'expires_at': 200, 'max_uses': 1}
        body.update(changes)
        return {'body': body, 'signature': base64.b64encode(self.key.sign(canonical(body))).decode()}

    def test_owner_signature_allows_exact_operation_once(self):
        self.assertEqual(self.auth.claim(self.grant(), self.operation), 'nonce-000001')
        with self.assertRaises(AuthorityDenied):
            self.auth.claim(self.grant(), self.operation)

    def test_replay_survives_restart(self):
        self.auth.claim(self.grant(), self.operation)
        restarted = ExternalAuthority(self.auth.public_keys, self.ledger, clock=lambda: 100)
        with self.assertRaises(AuthorityDenied):
            restarted.claim(self.grant(), self.operation)

    def test_forged_signature_denied(self):
        grant = self.grant()
        grant['signature'] = base64.b64encode(bytes(64)).decode()
        with self.assertRaises(AuthorityDenied):
            self.auth.claim(grant, self.operation)

    def test_unknown_owner_denied(self):
        auth = ExternalAuthority({}, self.ledger, clock=lambda: 100)
        with self.assertRaises(AuthorityDenied):
            auth.claim(self.grant(), self.operation)

    def test_expiry_denied(self):
        with self.assertRaises(AuthorityDenied):
            self.auth.claim(self.grant(expires_at=100), self.operation)

    def test_each_bound_field_change_denied_without_consumption(self):
        for field in self.operation:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.operation)
                changed[field] = ['tampered'] if isinstance(changed[field], list) else 'tampered'
                with self.assertRaises(AuthorityDenied):
                    self.auth.claim(self.grant(), changed)
        self.assertEqual(self.auth.claim(self.grant(), self.operation), 'nonce-000001')

    def test_unknown_fields_and_reusable_grants_denied(self):
        for grant in (self.grant(max_uses=2), {**self.grant(), 'approved': True}, self.grant(untrusted_approval='yes')):
            with self.assertRaises(AuthorityDenied):
                self.auth.claim(grant, self.operation)

    def test_typed_approved_or_boolean_not_authority(self):
        for grant in (True, {'approved': True}, {'body': {}, 'signature': ''}):
            with self.assertRaises(AuthorityDenied):
                self.auth.claim(grant, self.operation)

    def test_concurrent_claim_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        grant = self.grant()

        def attempt():
            try:
                return self.auth.claim(grant, self.operation)
            except AuthorityDenied:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(results.count('nonce-000001'), 1)
        self.assertEqual(results.count(None), 1)

    def test_invalid_grant_cannot_create_ledger(self):
        with self.assertRaises(AuthorityDenied):
            self.auth.claim({'approved': True}, self.operation)
        self.assertFalse(self.ledger.exists())

    def test_symlink_or_public_ledger_denied(self):
        target = Path(self.temp.name)/'target'
        target.write_text('do not change')
        self.ledger.symlink_to(target)
        with self.assertRaises(AuthorityDenied):
            self.auth.claim(self.grant(), self.operation)
        self.assertEqual(target.read_text(), 'do not change')
        self.ledger.unlink()
        self.ledger.write_text('')
        self.ledger.chmod(0o644)
        with self.assertRaises(AuthorityDenied):
            self.auth.claim(self.grant(), self.operation)

    def test_nonce_corruption_and_nonfinite_time_denied(self):
        nonfinite = self.grant()
        nonfinite['body']['expires_at'] = float('inf')
        for grant, now in ((self.grant(nonce='../escape'), 100), (nonfinite, 100), (self.grant(), float('nan'))):
            with self.assertRaises(AuthorityDenied):
                ExternalAuthority(self.auth.public_keys, self.ledger, clock=lambda: now).claim(grant, self.operation)


if __name__ == '__main__':
    unittest.main()

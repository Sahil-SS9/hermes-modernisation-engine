#!/usr/bin/env python3
"""Preparation refuses existing owner state before touching disposable roots.

Both current and preserved pre-fix control source can be tested. All paths are
fresh scratch fixtures, identity discovery is inert, and cloning is forbidden.
No real owner, ledger, signature, container, network or repository is changed.
"""

import argparse
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
parser = argparse.ArgumentParser()
parser.add_argument('--before-fix', action='store_true')
OPTIONS = parser.parse_args()
SOURCE = ROOT / ('controller-preserved/before-controller-fixes-1792373165286865850/prepare-trial-v5.py' if OPTIONS.before_fix else 'prepare-trial-v5.py')
spec = importlib.util.spec_from_file_location('controller_preparation_guard_target', SOURCE)
TARGET = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TARGET)


class PreparationGuardTests(unittest.TestCase):
    def exercise(self, claim_exists):
        with tempfile.TemporaryDirectory(prefix='controller-v5-preparation-', dir=os.environ['TMPDIR']) as raw:
            root = Path(raw)
            disposable, executor = root / 'disposable', root / 'executor'
            disposable.mkdir()
            executor.mkdir()
            ledger = executor / 'claims' / 'claims.sqlite'
            sign_dir = root / 'signatures'
            if claim_exists:
                ledger.parent.mkdir()
                ledger.write_bytes(b'fixture: existing claim state must not be moved')
            else:
                sign_dir.mkdir()
                (sign_dir / 'trial-v5-signatures.txt').write_text('fixture: existing owner signature')
            fresh_clone = Mock(side_effect=AssertionError('fixture forbids cloning/building/execution'))
            with (
                patch.object(TARGET, '_verify_identities', return_value={}),
                patch.object(TARGET, 'DISPOSABLE', disposable),
                patch.object(TARGET, 'EXEC_ROOT', executor),
                patch.object(TARGET, 'LEDGER', ledger),
                patch.object(TARGET, 'SIGN_DIR', str(sign_dir)),
                patch.object(TARGET, '_fresh_clone', fresh_clone),
            ):
                self.assertEqual(TARGET.main(), 1)
            fresh_clone.assert_not_called()
            self.assertTrue(executor.is_dir(), 'existing executor root must not be renamed')
            self.assertTrue(disposable.is_dir(), 'existing disposable root must not be renamed')
            if claim_exists:
                self.assertEqual(ledger.read_bytes(), b'fixture: existing claim state must not be moved')
            else:
                self.assertEqual((sign_dir / 'trial-v5-signatures.txt').read_text(), 'fixture: existing owner signature')

    def test_existing_claim_state_cannot_be_reset_by_preparation(self):
        self.exercise(claim_exists=True)

    def test_existing_owner_signature_blocks_preparation(self):
        self.exercise(claim_exists=False)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PreparationGuardTests))
    receipt = ROOT / 'controller-evidence' / f'preparation-guard-{time.time_ns()}.json'
    receipt.write_text(json.dumps({
        'scope': 'preparation state-protection fixtures only; no real state or execution',
        'before_fix_preserved_source': OPTIONS.before_fix, 'source': str(SOURCE),
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
    }, sort_keys=True, indent=2) + '\n')
    print('CONTROLLER_RECEIPT', receipt)
    raise SystemExit(0 if result.wasSuccessful() else 1)

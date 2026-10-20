#!/usr/bin/env python3
"""Controller-owned trial-flow regression witnesses. NO real execution/authority.

The Executor and authority are replaced with explicit, non-executing fixtures.
Historical v4 output is REPLAYED through the real committed Engine record/compare
in a fresh private temporary store. This does not run the project, Docker, its
pytest suite, or any owner-signed operation. The live request set/store/ledgers
and owner account are never written. Identity preflight is checked separately.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
APPROVAL = ROOT / 'requests/trial-v5-1792372144283845183'
SPEC = importlib.util.spec_from_file_location('controller_trial_flow_target', ROOT / 'run-trial-v5.py')
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)

from hermes_modernisation.service import Engine  # noqa: E402
from hermes_modernisation.store import Store  # noqa: E402

LIVE = json.loads((APPROVAL / 'manifest.json').read_bytes())
HISTORICAL = TARGET.prep.V4_EVIDENCE / 'output.bin'
OBSERVATIONS = []


class TrialFlowTests(unittest.TestCase):
    def exercise(self, add_legacy_data_dir_alias):
        # All created files and Engine state stay inside this new disposable root.
        with tempfile.TemporaryDirectory(prefix='controller-v5-flow-', dir=os.environ['TMPDIR']) as raw:
            temporary = Path(raw)
            private = temporary / 'engine-data'
            engine = Engine(private)
            job = engine.invoke('assess', {
                'repo': LIVE['clone']['path'],
                'goal': 'controller fixture: historical output replay, not project execution',
                'request_id': 'controller-flow-' + str(time.time_ns()),
            })
            manifest = copy.deepcopy(LIVE)
            manifest['assessment']['job_id'] = job['job_id']
            manifest['assessment']['data_dir'] = str(private)
            manifest['execution']['engine_data_dir'] = str(private)
            manifest['execution']['executor_root'] = str(temporary / 'fixture-attempts')
            manifest['execution']['ledger'] = str(temporary / 'NEVER-CREATE-CLAIMS.sqlite')
            if add_legacy_data_dir_alias:
                # Test-only isolation of the later stale-row defect. This does
                # not change or repair the actual owner manifest.
                manifest['execution']['data_dir'] = str(private)
            approval = temporary / 'fixture-requests'
            approval.mkdir()
            (approval / 'manifest.json').write_text(json.dumps(manifest))
            for phase in ('baseline', 'candidate'):
                (approval / f'{phase}.request.json').write_bytes(
                    (APPROVAL / f'{phase}.request.json').read_bytes()
                )
            calls = []
            historical = HISTORICAL.read_bytes()

            class FixtureAuthority:
                def __init__(self, *args, **kwargs):
                    pass

                def claim(self, *args, **kwargs):
                    # Only the post-run replay-refusal branch reaches this seam.
                    raise TARGET.approvals.AuthorityDenied('fixture-only replay refusal')

            class FixtureExecutor:
                def __init__(self, authority, root, image, *, profile, phase):
                    self.root, self.phase = Path(root), phase

                def run(self, grant, operation, source, oracle):
                    calls.append(self.phase)
                    attempt = self.root / operation['attempt_id']
                    attempt.mkdir(parents=True)
                    (attempt / 'output.bin').write_bytes(historical)
                    return {
                        'fixture_only': True,
                        'process_exit_code': 0,
                        'timed_out': False,
                        'truncated': False,
                        'container_removed': True,
                        'source_unchanged': True,
                        'output_sha256': hashlib.sha256(historical).hexdigest(),
                        'output_bytes': len(historical),
                    }

            def fixture_engine_cli(*args):
                self.assertEqual(args[0], '--data-dir')
                self.assertEqual(Path(args[1]), private)
                action = args[2]
                fields = {}
                for index in range(3, len(args), 2):
                    key, value = args[index][2:].replace('-', '_'), args[index + 1]
                    fields[key] = json.loads(value) if key == 'expectation' else value
                return Engine(private).invoke(action, fields)

            observation = {
                'case': self.id(),
                'fixture_only': True,
                'actual_project_executions': 0,
                'owner_signatures_used': 0,
                'real_authority_claims': 0,
                'source_output': str(HISTORICAL),
                'legacy_alias_added_only_in_test': add_legacy_data_dir_alias,
            }
            try:
                with (
                    patch.object(TARGET.prep, '_verify_identities', return_value={}),
                    patch.object(TARGET, '_verify_approval', return_value=manifest),
                    patch.object(TARGET, '_signatures', return_value={
                        'baseline': 'FIXTURE-NOT-A-SIGNATURE',
                        'candidate': 'FIXTURE-NOT-A-SIGNATURE',
                    }),
                    patch.object(TARGET.approvals, 'ExternalAuthority', FixtureAuthority),
                    patch.object(TARGET.executor_module, 'Executor', FixtureExecutor),
                    patch.object(TARGET, '_engine_cli', side_effect=fixture_engine_cli),
                    patch.object(TARGET, '_containers_clean', return_value={
                        'fixture_only': True, 'our_containers_remaining': [],
                    }),
                    patch.object(TARGET, 'TRIAL_ROOT', temporary),
                    patch.object(TARGET.subprocess, 'run', side_effect=AssertionError(
                        'Controller fixture forbids subprocess, Docker and real execution'
                    )),
                ):
                    exit_code = TARGET.main([str(approval)])
                    self.assertEqual(exit_code, 0)
                self.assertEqual(calls, ['baseline', 'candidate'])
                phases = [row['phase'] for row in Store(private).evidence_for(job['job_id'])]
                self.assertEqual(phases, ['baseline', 'candidate'])
                self.assertTrue((approval / 'evidence' / 'comparison.json').is_file())
                observation['status'] = 'PASS'
            except KeyError as error:
                observation['status'] = 'FAIL'
                observation['missing_key'] = str(error)
                self.fail('Trial control flow cannot finish: missing key ' + str(error))
            finally:
                observation['fixture_executor_calls'] = list(calls)
                observation['persisted_fixture_phases'] = [
                    row['phase'] for row in Store(private).evidence_for(job['job_id'])
                ]
                observation['claims_file_created'] = Path(manifest['execution']['ledger']).exists()
                OBSERVATIONS.append(observation)

    def test_unmodified_generated_manifest_can_complete_control_flow(self):
        self.exercise(add_legacy_data_dir_alias=False)

    def test_both_recorded_phases_reach_final_evidence_and_result(self):
        self.exercise(add_legacy_data_dir_alias=True)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TrialFlowTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = ROOT / 'controller-evidence'
    evidence.mkdir(exist_ok=True)
    receipt = evidence / f'flow-regression-{time.time_ns()}.json'
    receipt.write_text(json.dumps({
        'runner_sha256': hashlib.sha256((ROOT / 'run-trial-v5.py').read_bytes()).hexdigest(),
        'actual_project_executions': 0,
        'scope': 'control-flow fixtures and historical output replay only',
        'tests': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'observations': OBSERVATIONS,
    }, sort_keys=True, indent=2) + '\n')
    print('CONTROLLER_RECEIPT', receipt)
    raise SystemExit(0 if result.wasSuccessful() else 1)

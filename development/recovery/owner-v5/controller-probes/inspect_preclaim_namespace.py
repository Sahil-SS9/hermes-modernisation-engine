#!/usr/bin/env python3
"""Read-only live inspection plus isolated proof of pre-claim namespace recovery.

NO live authority is claimed and NO live directory is renamed by this program.
The reproduction uses a tiny scratch source, fake rootless-info response, and
an authority that always refuses at the exact same boundary. No container can
be created. This is infrastructure diagnosis, not a project-test result.
"""

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
ENGINE = Path('/home/kensei/repos/hermes-modernisation-engine')
sys.path.insert(0, str(ENGINE / 'src'))
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import dumps
from hermes_modernisation.store import Store


class FixtureAuthorityBoundary(RuntimeError):
    pass


class RefusingFixtureAuthority:
    def __init__(self):
        self.calls = 0

    def claim(self, grant, operation):
        self.calls += 1
        raise FixtureAuthorityBoundary('fixture refusal before any authority/state/container use')


def fixture_proof():
    # Sandbox policy correctly forbids source mounts from .hermes/config trees.
    # Use the already-authorised control workspace for this source fixture;
    # keep the native containment policy unchanged. This fixture never launches.
    with tempfile.TemporaryDirectory(prefix='preclaim-namespace-proof-', dir=ROOT / 'evidence/scratch') as raw:
        root = Path(raw)
        source = root / 'source'
        source.mkdir()
        (source / 'sentinel.txt').write_text('fixture: no executable project code\n')
        oracle = root / 'oracle.json'
        oracle.write_bytes(b'{}')
        authority = RefusingFixtureAuthority()
        image = 'fixture-image@sha256:' + 'a' * 64
        manager = Executor(authority, root / 'executor', image, profile='default', phase='baseline')
        source_identity = snapshot(source)['digest']
        operation = {
            'schema_version': 1, 'job_id': 'fixture-job', 'attempt_id': 'fixture-attempt',
            'actor': 'fixture-owner', 'profile': 'default', 'source_digest': source_identity,
            'candidate_digest': source_identity, 'oracle_digest': hashlib.sha256(oracle.read_bytes()).hexdigest(),
            'environment_digest': '0' * 64, 'image_digest': 'a' * 64, 'argv': ['/bin/true'],
            'read_roots': ['/source'], 'write_roots': ['/tmp', '/work'], 'network': 'none',
            'timeout_seconds': 1, 'output_limit_bytes': 1024,
        }
        operation['environment_digest'] = hashlib.sha256(dumps(manager.environment(operation))).hexdigest()
        commands = []

        def rootless_info_only(command, *args, **kwargs):
            commands.append(command)
            if command == ['docker', 'info', '--format', '{{json .SecurityOptions}}']:
                return subprocess.CompletedProcess(command, 0, '["name=rootless"]', '')
            raise AssertionError('fixture forbids container operations: ' + repr(command))

        outcomes = []
        with patch('hermes_modernisation.executor.subprocess.run', side_effect=rootless_info_only):
            for expected in (FixtureAuthorityBoundary, FileExistsError):
                try:
                    manager.run({}, operation, source, oracle)
                except expected as error:
                    outcomes.append(type(error).__name__)
                else:
                    raise AssertionError('expected pre-claim refusal was not observed')
            attempt = manager.root / operation['attempt_id']
            assert sorted(p.name for p in attempt.iterdir()) == ['source']
            assert snapshot(attempt / 'source')['digest'] == source_identity
            preserved = manager.root / 'fixture-preclaim-source-PRESERVED'
            attempt.rename(preserved)  # scratch fixture ONLY, never the live path
            try:
                manager.run({}, operation, source, oracle)
            except FixtureAuthorityBoundary as error:
                outcomes.append(type(error).__name__)
            else:
                raise AssertionError('recovery did not reach the same unconsumed authority boundary')
        assert authority.calls == 2
        assert outcomes == ['FixtureAuthorityBoundary', 'FileExistsError', 'FixtureAuthorityBoundary']
        assert preserved.is_dir() and snapshot(preserved / 'source')['digest'] == source_identity
        return {'fixture_only': True, 'outcomes': outcomes, 'authority_boundary_calls': authority.calls,
                'container_operations': 0, 'preserved_source_digest_matches': True,
                'one_changed_variable': 'preserved occupied attempt directory; operation/source/core/authority unchanged'}


def main():
    state = json.loads((ROOT / 'ACTIVE-PACKAGE.json').read_bytes())
    approval = Path(state['approval_directory'])
    manifest = json.loads((approval / 'manifest.json').read_bytes())
    execution_root = Path(manifest['execution']['executor_root'])
    baseline = execution_root / manifest['requests']['baseline']['attempt_id']
    candidate = execution_root / manifest['requests']['candidate']['attempt_id']
    ledger = Path(manifest['execution']['ledger'])
    info = baseline.lstat()
    assert stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not baseline.is_symlink()
    assert stat.S_IMODE(info.st_mode) == 0o700
    entries = sorted(p.name for p in baseline.iterdir())
    assert entries == ['source'], 'not a source-only pre-claim directory; stop for inspection'
    assert not candidate.exists() and not candidate.is_symlink()
    assert not any(Path(str(ledger) + suffix).exists() for suffix in ('', '-wal', '-shm', '-journal'))
    frozen = snapshot(baseline / 'source')['digest']
    live = snapshot(Path(manifest['clone']['path']))['digest']
    expected = manifest['requests']['baseline']['source_digest']
    assert frozen == live == expected
    stored = Store(Path(manifest['execution']['engine_data_dir'])).evidence_for(manifest['assessment']['job_id'])
    assert stored == [], 'prior phase evidence exists; do not restart the trial'
    negative_log = ROOT / 'evidence/scratch/trialv5-negative.log'
    diagnosis = {
        'live_inspection_read_only': True, 'owner_key_accessed': False,
        'attempt': str(baseline), 'entries': entries, 'candidate_attempt_absent': True,
        'ledger_and_journals_absent': True, 'stored_phases': [],
        'frozen_source_digest': frozen, 'live_source_digest': live, 'signed_source_digest': expected,
        'attempt_mtime_ns': info.st_mtime_ns,
        'earlier_rejected_signature_log': str(negative_log),
        'earlier_rejected_signature_output': negative_log.read_text().strip(),
        'earlier_rejected_signature_log_mtime_ns': negative_log.stat().st_mtime_ns,
        'failure_position': 'Executor.run attempt.mkdir line112, before authority.claim line156 and docker create line170',
        'fixture_proof': fixture_proof(),
        'safe_recovery_preconditions_met': True,
    }
    target = ROOT / 'controller-evidence' / f'preclaim-namespace-inspection-{time.time_ns()}.json'
    target.write_text(json.dumps(diagnosis, sort_keys=True, indent=2) + '\n')
    print(json.dumps(diagnosis, sort_keys=True, indent=2))
    print('DIAGNOSTIC_RECEIPT', target)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Verify the completed REAL trial using retained artifacts and read-only state.

Does not run project code, claim/replay authority, modify any original receipt,
change an input or read private keys. Writes only a new additive evidence packet.
"""

import base64
import hashlib
import importlib.util
import json
import re
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
EVIDENCE = ROOT / 'owner-executor-v5/trial-v5-evidence-1792396212791001882'
state = json.loads((ROOT / 'ACTIVE-PACKAGE.json').read_bytes())
approval = Path(state['approval_directory'])
manifest = json.loads((approval / 'manifest.json').read_bytes())
expected = json.loads((ROOT / 'EXPECTED-CASES-V4.json').read_bytes())
expected_ids = {tuple(case) for case in expected['cases']}
assert len(expected_ids) == len(expected['cases'])

spec = importlib.util.spec_from_file_location('postrun_trial_v5', ROOT / 'run-trial-v5.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.prep._verify_identities()
manifest['_approval_dir'] = str(approval)
runner._signatures(Path(runner.DEFAULT_SIGNATURES), manifest, hashlib.sha256((approval / 'manifest.json').read_bytes()).hexdigest())
# Verify package + both request signatures again, without invoking claim.

from hermes_modernisation.approvals import canonical
from hermes_modernisation.identity import snapshot


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(name):
    return json.loads((EVIDENCE / name).read_bytes())


def checked_command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise AssertionError((args, result.returncode, result.stderr))
    return result.stdout


connection = sqlite3.connect('file:' + manifest['execution']['ledger'] + '?mode=ro', uri=True)
try:
    claims = connection.execute('SELECT actor,nonce,operation,claimed_at FROM claims ORDER BY claimed_at').fetchall()
    schema = connection.execute("SELECT sql FROM sqlite_master WHERE name='claims'").fetchone()[0]
finally:
    connection.close()
assert len(claims) == len(manifest['requests']) == 2
assert 'PRIMARY KEY(actor, nonce)' in schema
claim_map = {(actor, nonce): (operation, at) for actor, nonce, operation, at in claims}
assert len(claim_map) == len(claims)

security = json.loads(checked_command(['docker', 'info', '--format', '{{json .SecurityOptions}}']))
assert 'name=rootless' in security
live_container_names = checked_command(['docker', 'ps', '-a', '--filter', 'name=modernise-', '--format', '{{.Names}}']).split()

phases = {}
copies = {}
for phase in ('baseline', 'candidate'):
    request_raw = (approval / f'{phase}.request.json').read_bytes()
    body = json.loads(request_raw)
    operation = body['operation']
    receipt = read_json(f'{phase}-receipt.json')
    attempt = Path(manifest['execution']['executor_root']) / operation['attempt_id']
    assert (attempt / 'receipt.json').read_bytes() == (EVIDENCE / f'{phase}-receipt.json').read_bytes()
    assert receipt['phase'] == phase and receipt['actor'] == operation['actor']
    assert receipt['authority_nonce'] == body['nonce']
    assert receipt['process_exit_code'] == 0 and receipt['container_removed'] is True
    assert receipt['source_unchanged'] is True and receipt['timed_out'] is receipt['truncated'] is False
    assert receipt['source_digest'] == operation['source_digest']
    assert receipt['environment_digest'] == operation['environment_digest']
    assert receipt['verdict'] == 'NOT_PROVEN' and receipt['grade'] == 'observed-process-only'
    stored_operation, claimed_at = claim_map[(operation['actor'], body['nonce'])]
    assert bytes(stored_operation) == canonical(operation)
    source = Path(manifest['clone']['path'] if phase == 'baseline' else manifest['recipe']['root'])
    assert snapshot(source)['digest'] == operation['source_digest']
    output = (attempt / 'output.bin').read_bytes()
    assert len(output) == receipt['output_bytes'] and sha(output) == receipt['output_sha256']
    lines = output.decode('utf-8').splitlines()
    start, end = lines.index('RUNNER_JUNIT_BEGIN'), lines.index('RUNNER_JUNIT_END')
    assert start + 2 == end and lines.count('RUNNER_JUNIT_BEGIN') == lines.count('RUNNER_JUNIT_END') == 1
    junit = base64.b64decode(lines[start + 1], validate=True)
    assert junit == (EVIDENCE / f'{phase}-junit.xml').read_bytes()
    assert b'<!DOCTYPE' not in junit and len(junit) <= 1048576
    cases = list(ET.fromstring(junit).iter('testcase'))
    ids = [(case.get('classname', ''), case.get('name', '')) for case in cases]
    assert len(set(ids)) == len(ids) and set(ids) == expected_ids
    failures = sum(case.find('failure') is not None for case in cases)
    errors = sum(case.find('error') is not None for case in cases)
    skips = sum(case.find('skipped') is not None for case in cases)
    assert failures == errors == skips == 0
    evaluation = read_json(f'{phase}-evaluation.json')
    record = read_json(f'{phase}-record.json')
    assert evaluation['accepted'] is record['accepted'] is True
    container = json.loads((attempt / 'container.json').read_bytes())
    identifier = container['container_id']
    assert re.fullmatch('[a-f0-9]{64}', identifier)
    removed = subprocess.run(['docker', 'container', 'inspect', identifier], capture_output=True, text=True, timeout=30)
    assert removed.returncode != 0 and 'No such' in removed.stderr
    assert container['name'] not in live_container_names
    console = lines[:start] + lines[end + 1:]
    console = [line for line in console if not line.startswith('RUNNER_')]
    header = [line for line in console if line.startswith(('platform ', 'plugins:', 'rootdir:', 'configfile:'))]
    notices = [line for line in console if re.search(r'(?i)\b(?:[a-z]*warning|deprecated)\b', line)]
    phases[phase] = {
        'tests': len(cases), 'passed': len(cases) - failures - errors - skips,
        'failures': failures, 'errors': errors, 'skipped': skips,
        'case_ids': [list(case) for case in sorted(ids)],
        'process_exit': receipt['process_exit_code'], 'duration_seconds': receipt['duration_seconds'],
        'warnings_in_evaluation': evaluation.get('warnings_count', 0),
        'additional_console_notice_lines': notices, 'pytest_header': header,
        'container_id': identifier, 'container_removed_confirmed': True,
        'claim_nonce': body['nonce'], 'claimed_at': claimed_at,
        'source_digest': operation['source_digest'], 'output_sha256': sha(output),
    }
    for filename in ('output.bin', 'container.json', 'attempt.json'):
        copies[f'{phase}-{filename}'] = (attempt / filename).read_bytes()
    copies[f'{phase}.request.json'] = request_raw
    print(phase.upper(), json.dumps({key: value for key, value in phases[phase].items() if key != 'case_ids'}, sort_keys=True))
    print(phase.upper() + '_REAL_RETAINED_CONSOLE', '\n'.join(console))

assert phases['baseline']['claimed_at'] < phases['candidate']['claimed_at']
comparison = read_json('comparison.json')
assert comparison['verdict'] == 'NOT_PROVEN'
assert comparison['comparison']['verdict'] == 'SAME_SELECTED_SCOPE'
assert comparison['compared_cases'] == len(expected_ids)
assert len(comparison['comparison']['cases']) == len(expected_ids)
assert all(case['before'] == case['after'] == 'passed' for case in comparison['comparison']['cases'])
assert read_json('replay-refusal-proof.json')['refused'] is True
cleanup = read_json('container-cleanup.json')
assert cleanup['our_containers_remaining'] == []
for name in cleanup['attempt_container_names']:
    assert name not in live_container_names
for repo, head in ((runner.prep.ENGINE, runner.prep.ENGINE_COMMIT), (runner.prep.ORIGINAL, runner.prep.ORIGINAL_HEAD)):
    assert checked_command(['git', '-C', str(repo), 'rev-parse', 'HEAD']).strip() == head
    assert checked_command(['git', '-C', str(repo), 'status', '--porcelain']) == ''

packet = approval / 'evidence' / ('controller-verification-' + str(time.time_ns()))
packet.mkdir(mode=0o755)
for path in EVIDENCE.iterdir():
    if path.is_file():
        copies[path.name] = path.read_bytes()
copies['owner-public.pem'] = runner.prep.ENROLLED_PEM.read_bytes()
copies['owner-public-signatures.txt'] = Path(runner.DEFAULT_SIGNATURES).read_bytes()
summary = {
    'state': 'REAL_TRIAL_PASSED_SELECTED_SCOPE', 'project_executions': 2,
    'owner_package_and_both_signatures_reverified': True,
    'claim_rows': len(claims), 'duplicate_claims': len(claims) - len(claim_map),
    'phases': phases, 'identical_expected_case_set': True,
    'comparison_inner': comparison['comparison']['verdict'], 'proof_verdict': comparison['verdict'],
    'no_project_code_executed_by_this_verifier': True,
    'container_removal_verified_by_actual_ids': True, 'rootless_runtime': True,
    'both_original_repositories_clean_and_pinned': True,
    'original_evidence': str(EVIDENCE), 'verification_packet': str(packet),
    'limitations': ['selected 20 cases only', 'candidate-authored reports, not protected independent capture',
                    'no full-engine completion, installation, deployment or publication claim'],
}
copies['controller-verification.json'] = (json.dumps(summary, sort_keys=True, indent=2) + '\n').encode()
for name, raw in copies.items():
    (packet / name).write_bytes(raw)
    (packet / name).chmod(0o644)
# Replace only the COPIED checksum file with the additive packet's own set.
sums = ''.join(f'{sha(path.read_bytes())}  {path.name}\n' for path in sorted(packet.iterdir()) if path.name != 'SHA256SUMS')
(packet / 'SHA256SUMS').write_text(sums)
(packet / 'SHA256SUMS').chmod(0o644)
print('VERIFIED_REAL_PROJECT_EXECUTIONS', summary['project_executions'])
print('VERIFICATION_PACKET', packet)
print('OWNER_AUTHORITY_CLAIM_ROWS', len(claims))

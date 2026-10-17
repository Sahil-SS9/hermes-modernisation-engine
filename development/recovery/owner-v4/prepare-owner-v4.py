"""Prepare a fresh exact v4 CANDIDATE-ONLY owner request; v4 reuses the accepted v3 baseline; never signs or executes source code.

v3 differs from v2 only in the signed in-container program (walkie-program-v3.py),
which additionally prints the raw JUnit bytes (bounded, base64, SHA-256) to the
retained stdout so the trusted host-side evaluator can check exact per-case
identities. Same images, sources, oracle, sandbox, limits and engine core.
"""
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

CONTROL=Path(__file__).parent
ENGINE=Path('/home/kensei/repos/hermes-modernisation-engine')
sys.path.insert(0,str(ENGINE/'src'))
from hermes_modernisation.approvals import canonical
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot

out=Path('/home/kensei/handoff/agent-plugin-plans/approvals')/('walkie-v4-'+str(time.time_ns()))
out.mkdir(mode=0o755)
oracle=CONTROL/'walkie-regression-oracle-v2.json'
contract=json.loads(oracle.read_text())
program=(CONTROL/'walkie-program-v3.py').read_text()
expected=CONTROL/'walkie-expected-cases-v3.json'
evaluator=CONTROL/'walkie_evidence_v3.py'
entries={
 'candidate':(Path('/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie'),'modernise-walkie-candidate@sha256:b3613f1f72f20834961fef5230fb80059a6f4ef6ac89464af15bc13cd9795b26','/candidate/.venv/bin/python')}
expires_at=int(time.time())+172800
manifest={'scope':'owner-request preparation only; nothing executed or approved',
  'baseline_reused':'v3 baseline attempt baseline-be7e5521c78244fb86310464eabe8ffd (accepted 17/10/2026)',
  'change_from_v3':'candidate dependency follow-up only: pytest-asyncio 1.4.0, starlette 0.52.1 (commit c6134c2); same program, oracle, tests, sandbox',
  'program_sha256':hashlib.sha256(program.encode()).hexdigest(),
  'expected_cases_sha256':hashlib.sha256(expected.read_bytes()).hexdigest(),
  'trusted_evaluator_sha256':hashlib.sha256(evaluator.read_bytes()).hexdigest(),
  'requests':{},'executor_core_digest':snapshot(ENGINE/'src/hermes_modernisation')['digest']}
for phase,(source,image,python) in entries.items():
    for record in contract['files']:
        assert hashlib.sha256((source/record['path']).read_bytes()).hexdigest()==record['sha256']
    digest=snapshot(source)['digest']
    operation={'schema_version':1,'job_id':'walkie-python314-fastapi-v4','attempt_id':phase+'-'+uuid.uuid4().hex,
      'actor':'sahil','profile':'default','source_digest':digest,'candidate_digest':digest,
      'oracle_digest':hashlib.sha256(oracle.read_bytes()).hexdigest(),'image_digest':image.split('@sha256:')[1],
      'argv':[python,'-B','-c',program],'read_roots':['/source'],'write_roots':['/tmp','/work'],
      'network':'none','timeout_seconds':120,'output_limit_bytes':4194304}
    executor=Executor(None,CONTROL/'owner-executor-v4',image,profile='default',phase=phase)
    environment=executor.environment(operation)
    operation['environment_digest']=hashlib.sha256(canonical(environment)).hexdigest()
    executor.prepare(operation,source,oracle)
    body={'schema_version':1,'operation':operation,'nonce':uuid.uuid4().hex,'expires_at':expires_at,'max_uses':1}
    path=out/(phase+'-request.json')
    with path.open('xb') as stream:stream.write(canonical(body))
    manifest['requests'][phase]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'source':str(source),'image':image,'environment':environment,'expires_at':expires_at,'signature_received':False}
with (out/'manifest.json').open('x') as stream:json.dump(manifest,stream,indent=2)
expiry=time.strftime('%A %d %B %Y %H:%M:%S %Z',time.localtime(expires_at))
readme=f'''Modernisation follow-up approval gate (v4, upgraded copy only)

Approves ONE isolated test run: the upgraded walkie-talkie copy with two test tools updated (pytest-asyncio 1.4.0, starlette 0.52.1), same 20 tests, no network, read-only, non-root, 512 MB, 2-minute cap. Compared against the original run already accepted on 17/10. One-use, expires {expiry}.
'''
(out/'READ-ME-FIRST.txt').write_text(readme)
print(json.dumps({k:v for k,v in manifest.items() if k!='requests'}|{'requests':{p:{'sha256':r['sha256'],'expires_at':r['expires_at']} for p,r in manifest['requests'].items()}},indent=2))
print('APPROVAL_DIRECTORY='+str(out))

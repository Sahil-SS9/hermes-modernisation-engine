"""Prepare fresh exact v3 owner requests only; never signs or executes source code.

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

out=Path('/home/kensei/handoff/agent-plugin-plans/approvals')/('walkie-v3-'+str(time.time_ns()))
out.mkdir(mode=0o755)
oracle=CONTROL/'walkie-regression-oracle-v2.json'
contract=json.loads(oracle.read_text())
program=(CONTROL/'walkie-program-v3.py').read_text()
expected=CONTROL/'walkie-expected-cases-v3.json'
evaluator=CONTROL/'walkie_evidence_v3.py'
entries={
 'baseline':(CONTROL/'baseline-source-v2','modernise-sandbox-dev@sha256:49808cb0b9909505e906fcef5e0ea373566c96a0508cbc3f60c2fc38de08217f','python'),
 'candidate':(Path('/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie'),'modernise-walkie-candidate@sha256:c934a26fb33c5dc74aa6c43ff93022604dd8add753fe4ffd7fbb31e162a4e999','/candidate/.venv/bin/python')}
expires_at=int(time.time())+172800
manifest={'scope':'owner-request preparation only; nothing executed or approved',
  'supersedes':'walkie-v2-1792072605580412472 (expired unsigned; never claimed)',
  'change_from_v2':'signed program also emits bounded raw JUnit for trusted per-case evaluation; candidate requires accepted baseline per-case evidence',
  'program_sha256':hashlib.sha256(program.encode()).hexdigest(),
  'expected_cases_sha256':hashlib.sha256(expected.read_bytes()).hexdigest(),
  'trusted_evaluator_sha256':hashlib.sha256(evaluator.read_bytes()).hexdigest(),
  'requests':{},'executor_core_digest':snapshot(ENGINE/'src/hermes_modernisation')['digest']}
for phase,(source,image,python) in entries.items():
    for record in contract['files']:
        assert hashlib.sha256((source/record['path']).read_bytes()).hexdigest()==record['sha256']
    digest=snapshot(source)['digest']
    operation={'schema_version':1,'job_id':'walkie-python314-fastapi-v3','attempt_id':phase+'-'+uuid.uuid4().hex,
      'actor':'sahil','profile':'default','source_digest':digest,'candidate_digest':digest,
      'oracle_digest':hashlib.sha256(oracle.read_bytes()).hexdigest(),'image_digest':image.split('@sha256:')[1],
      'argv':[python,'-B','-c',program],'read_roots':['/source'],'write_roots':['/tmp','/work'],
      'network':'none','timeout_seconds':120,'output_limit_bytes':4194304}
    executor=Executor(None,CONTROL/'owner-executor-v3',image,profile='default',phase=phase)
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
readme=f'''Modernisation real-regression approval gate (v3)

The engine preview is built, but the full engine is NOT complete.

This approval permits only two isolated test runs: the frozen original walkie-talkie API/auth slice (20 named tests), then the prepared Python 3.14/FastAPI candidate slice. Each run has a 120-second cap, network off, read-only source, non-root uid, 512 MB memory and a 4 MB output cap. No live repository, installation, push, merge or publishing. A pass on these 20 tests still does not prove full behavioural equivalence.

What changed from v2 (expired unsigned, never used): the test program now also prints the raw JUnit results to the retained output, so the operator-side evaluator can check each of the 20 expected test identities, not just totals. The candidate run is refused unless the baseline's per-case evidence was accepted first.

Read baseline-request.json, candidate-request.json and manifest.json in this directory before signing. Each request is one-use and expires {expiry}. Any changed source/executor/oracle/image/argv/environment invalidates the request.

Run the following in YOUR OWN terminal/account. It prompts for the path to your EXISTING owner.key, prints two signatures and never writes or displays the key. Do not paste the key or its contents into chat. The assistant must never run this command or read that private key.

bash -c 'set -euo pipefail; read -r -p "Path to your existing owner.key: " key; for phase in baseline candidate; do printf "%s: " "$phase"; openssl pkeyutl -sign -rawin -inkey "$key" -in "{out}/${{phase}}-request.json" | base64 -w0; printf "\\n"; done'

Return only the baseline: and candidate: signature lines.
'''
(out/'READ-ME-FIRST.txt').write_text(readme)
print(json.dumps({k:v for k,v in manifest.items() if k!='requests'}|{'requests':{p:{'sha256':r['sha256'],'expires_at':r['expires_at']} for p,r in manifest['requests'].items()}},indent=2))
print('APPROVAL_DIRECTORY='+str(out))

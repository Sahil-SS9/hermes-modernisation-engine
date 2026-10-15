"""Trusted operator control-plane acceptance. Workloads run only inside Docker.

Uses ephemeral synthetic fixture signing from a disposable signer container;
never enrols a real owner or authorises a real benchmark. Not a native SDK gate.
"""
import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).parent
ENGINE=Path('/home/kensei/repos/hermes-modernisation-engine')
sys.path.insert(0,str(ENGINE/'src'))
from hermes_modernisation.approvals import AuthorityDenied,ExternalAuthority,canonical
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot

IMAGE='modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6'
command=['docker','run','--rm','--init','--pull=never','--name','modernise-fixture-signer','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=256m','--memory-swap=256m','--cpus=1','--user=65534:65534','--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777','--env','HOME=/tmp','--env','PYTHONPATH=/engine/src','--mount',f'type=bind,src={ENGINE},dst=/engine,readonly,bind-recursive=disabled','--mount',f'type=bind,src={ROOT}/fixtures,dst=/fixtures,readonly,bind-recursive=disabled','--mount',f'type=bind,src={ROOT}/sign-fixtures.py,dst=/sign-fixtures.py,readonly',IMAGE,'python','-B','/sign-fixtures.py']
r=subprocess.run(command,capture_output=True,text=True,timeout=30)
assert r.returncode==0,r.stdout+r.stderr
fixture=json.loads(r.stdout)
assert fixture['scope']=='ephemeral synthetic fixtures only; not real owner approval'
parent=ROOT/('run-'+str(time.time_ns()));parent.mkdir(mode=0o700)
(parent/'fixture-grants.json').write_text(r.stdout);(parent/'fixture-grants.json').chmod(0o600)
authority_dir=parent/'authority';authority_dir.mkdir(mode=0o700)
authority=ExternalAuthority({'fixture':base64.b64decode(fixture['public_key'],validate=True)},authority_dir/'claims.sqlite')
executor=Executor(authority,parent/'attempts',IMAGE,profile='development-fixtures')
results={}
for name,grant in fixture['grants'].items():
    op=grant['body']['operation'];source=ROOT/'fixtures'/name
    before=snapshot(source)['digest']
    receipt=executor.run(grant,op,source,ROOT/'fixtures'/(name+'-oracle.json'))
    output=parent/'attempts'/op['attempt_id']/'output.bin'
    raw=output.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt['output_sha256']
    assert snapshot(source)['digest']==before==receipt['source_digest']
    assert receipt['container_removed'] and receipt['source_unchanged']
    assert receipt['grade']=='observed-process-only' and receipt['actor']=='fixture'
    assert receipt['verdict']=='NOT_PROVEN' and 'tests_passed' not in receipt
    if name=='success':
        assert receipt['process_exit_code']==0 and not receipt['truncated'] and not receipt['timed_out'],receipt
        assert json.loads(raw)=={'value':4,'protected_boundary':True},raw
    elif name=='output':
        assert receipt['truncated'] and len(raw)==1024,receipt
    elif name=='deadline':
        assert receipt['timed_out'] and b'spawned descendant' in raw,receipt
    try:authority.claim(grant,op)
    except AuthorityDenied:pass
    else:raise AssertionError('Spent fixture grant was accepted')
    results[name]=receipt
with sqlite3.connect(authority_dir/'claims.sqlite') as connection:
    rows=connection.execute('SELECT nonce,operation FROM claims').fetchall()
    assert len(rows)==len(results)==3
    for nonce,operation in rows:
        matched=[g['body']['operation'] for g in fixture['grants'].values() if g['body']['nonce']==nonce]
        assert len(matched)==1 and operation==canonical(matched[0])
summary={'scope':'real rootless Docker executor controls using fixture authority ONLY; no owner/benchmark/native caller proof',
    'results':results,'durable_claims_read_back':3,'replay_refused':True,'owner_authority_used':False,
    'operator_interpreter':sys.version,'raw_evidence_root':str(parent)}
(parent/'summary.json').write_text(json.dumps(summary,indent=2));(parent/'summary.json').chmod(0o600)
print(json.dumps(summary,indent=2))

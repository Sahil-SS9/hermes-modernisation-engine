"""Disposable fixture signer. No real owner key or authority is used."""
import base64
import hashlib
import json
import time
import uuid
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hermes_modernisation.approvals import ExternalAuthority, canonical
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import dumps

image='modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6'
key=Ed25519PrivateKey.generate()
public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
executor=Executor(ExternalAuthority({'fixture':public},Path('/tmp/unused.sqlite')),Path('/tmp/unused'),image,profile='development-fixtures')
records={}
for name in ('success','output','deadline'):
    source=Path('/fixtures')/name
    digest=snapshot(source)['digest']
    oracle=(Path('/fixtures')/(name+'-oracle.json')).read_bytes()
    operation={'schema_version':1,'job_id':'executor-fixture','attempt_id':name+'-'+uuid.uuid4().hex,
        'actor':'fixture','profile':'development-fixtures','source_digest':digest,'candidate_digest':digest,
        'oracle_digest':hashlib.sha256(oracle).hexdigest(),'image_digest':image.split('@sha256:')[1],
        'argv':['python','-B','/source/probe.py']+(['--rm'] if name=='success' else []),
        'read_roots':['/source'],'write_roots':['/tmp','/work'],'network':'none',
        'timeout_seconds':1 if name=='deadline' else 10,'output_limit_bytes':1024}
    operation['environment_digest']=hashlib.sha256(dumps(executor.environment(operation))).hexdigest()
    body={'schema_version':1,'operation':operation,'nonce':uuid.uuid4().hex,'expires_at':time.time()+300,'max_uses':1}
    records[name]={'body':body,'signature':base64.b64encode(key.sign(canonical(body))).decode()}
print(json.dumps({'scope':'ephemeral synthetic fixtures only; not real owner approval','public_key':base64.b64encode(public).decode(),'grants':records}))

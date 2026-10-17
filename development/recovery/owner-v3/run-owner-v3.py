"""External owner-gated v3 regression runner; no signing or approval endpoint.

Preflight is inert. Execution requires the separately provided exact signature.
Operator-only control code, never a native tool or candidate dependency.

v3 over v2: after the bounded process run, the trusted host-side evaluator
(walkie_evidence_v3) re-derives exact per-case JUnit evidence from the retained
output.bin and writes junit.xml + evaluation.json beside the receipt. The
candidate phase is refused unless the baseline attempt's retained output
re-evaluates as ACCEPTED here, in addition to the v2 receipt/claim checks.
"""
import argparse
import base64
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat,load_pem_public_key

CONTROL=Path(__file__).parent
ENGINE=Path('/home/kensei/repos/hermes-modernisation-engine')
REQUESTS=Path('/home/kensei/handoff/agent-plugin-plans/approvals/walkie-v3-1792267598341426808')
EXECUTOR_ROOT=CONTROL/'owner-executor-v3'
sys.path.insert(0,str(ENGINE/'src'))
sys.path.insert(0,str(CONTROL))
from hermes_modernisation.approvals import ExternalAuthority,canonical
from hermes_modernisation.executor import Executor
from hermes_modernisation.jsonio import loads

HASHES={'baseline':'c7a13e63dfe89816f3d31efa8490eb383606dc1ccfa604392a6bed718219400f',
        'candidate':'d990670fa3806a9144695a5b6d8ab759a0e0d8db53f5795686fac0ee9272fea8'}
PINNED_FILES={'walkie_evidence_v3.py':'7a4b94ac831d3b3a81229b91421ce192df27aca6a6c0532215423a81020ff55e',
              'walkie-expected-cases-v3.json':'24ba63ccc54bc808ac27c5ff911c8476ff54c30bcf6b8a52a536374526c770d6'}
SOURCES={'baseline':CONTROL/'baseline-source-v2','candidate':Path('/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie')}
IMAGES={'baseline':'modernise-sandbox-dev@sha256:49808cb0b9909505e906fcef5e0ea373566c96a0508cbc3f60c2fc38de08217f',
        'candidate':'modernise-walkie-candidate@sha256:c934a26fb33c5dc74aa6c43ff93022604dd8add753fe4ffd7fbb31e162a4e999'}
PUBLIC_SPKI='MCowBQYDK2VwAyEAKpMZpRxBfeT0ZqKa87hpT1kXdZCHnYK6hHqh0f6Fb+8='

for name,digest in PINNED_FILES.items():
    assert hashlib.sha256((CONTROL/name).read_bytes()).hexdigest()==digest,'Trusted evaluator input changed: '+name
import walkie_evidence_v3 as evidence  # noqa: E402  (imported only after its bytes are verified)

EXPECTED=evidence.load_expected((CONTROL/'walkie-expected-cases-v3.json').read_bytes())


def accept_baseline():
    """Re-evaluate the baseline attempt from retained bytes; never trust a stored verdict."""
    old_body=loads((REQUESTS/'baseline-request.json').read_bytes())
    old_op=old_body['operation']
    attempt=EXECUTOR_ROOT/old_op['attempt_id']
    receipt=loads((attempt/'receipt.json').read_bytes())
    assert receipt['actor']=='sahil' and receipt['phase']=='baseline' and receipt['process_exit_code']==0 and not receipt['timed_out'] and not receipt['truncated'] and receipt['container_removed'] and receipt['source_unchanged'],'Baseline process collection not accepted'
    raw=(attempt/'output.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt['output_sha256'],'Baseline output does not match its receipt'
    result,_=evidence.evaluate(raw,EXPECTED)
    assert result['accepted'],'Baseline per-case evidence not accepted: '+'; '.join(result['problems'])
    with sqlite3.connect((CONTROL/'authority/claims.sqlite').as_uri()+'?mode=ro',uri=True) as connection:
        row=connection.execute('SELECT operation FROM claims WHERE actor=? AND nonce=?',('sahil',old_body['nonce'])).fetchone()
        assert row is not None and row[0]==canonical(old_op),'Missing authentic baseline claim'
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['baseline','candidate'])
    parser.add_argument('--signature')
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    raw=(REQUESTS/(args.phase+'-request.json')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASHES[args.phase],'Request changed'
    body=loads(raw);assert canonical(body)==raw
    operation=body['operation']
    public=load_pem_public_key((CONTROL/'owner-public-key.pem').read_bytes())
    assert base64.b64encode(public.public_bytes(Encoding.DER,PublicFormat.SubjectPublicKeyInfo)).decode()==PUBLIC_SPKI,'Enrolled owner key changed'
    authority=ExternalAuthority({'sahil':public.public_bytes(Encoding.Raw,PublicFormat.Raw)},CONTROL/'authority/claims.sqlite')
    executor=Executor(authority,EXECUTOR_ROOT,IMAGES[args.phase],profile='default',phase=args.phase)
    source=SOURCES[args.phase];oracle=CONTROL/'walkie-regression-oracle-v2.json'
    contract=loads(oracle.read_bytes())
    for record in contract['files']:
        assert hashlib.sha256((source/record['path']).read_bytes()).hexdigest()==record['sha256'],'Protected original test changed'
    executor.prepare(operation,source,oracle)
    if args.preflight:
        assert args.signature is None,'Preflight never accepts/exercises signatures'
        print(json.dumps({'preflight':'PASS','phase':args.phase,'execution_performed':False,'authority_claimed':False,
                          'request_sha256':HASHES[args.phase],'expires_at':body['expires_at'],'trusted_inputs_pinned':True,
                          'expected_case_count':len(EXPECTED)}))
        return 0
    if not args.signature:parser.error('Authentic exact one-use owner signature required; no execution attempted')
    baseline_acceptance=accept_baseline() if args.phase=='candidate' else None
    grant={'body':body,'signature':args.signature}
    receipt=executor.run(grant,operation,source,oracle)
    attempt=EXECUTOR_ROOT/operation['attempt_id']
    raw_output=(attempt/'output.bin').read_bytes()
    assert hashlib.sha256(raw_output).hexdigest()==receipt['output_sha256']
    result,junit=evidence.evaluate(raw_output,EXPECTED)
    if junit is not None:
        Executor._write_bytes(attempt/'junit.xml',junit)
    Executor._write(attempt/'evaluation.json',result)
    observed_ok=receipt['process_exit_code']==0 and not receipt['timed_out'] and not receipt['truncated'] and receipt['source_unchanged'] and receipt['container_removed']
    summary={'phase':args.phase,'process_receipt':receipt,'observed_process_collection_ok':observed_ok,
             'per_case_evidence_accepted':result['accepted'],'per_case_problems':result['problems'],
             'derived_counts':result.get('derived_counts'),'warnings_count':result.get('warnings_count'),
             'junit_sha256':result.get('junit_sha256'),'evidence_grade':evidence.GRADE,
             'baseline_acceptance_rechecked':baseline_acceptance is not None,
             'scope':'20 existing original API/auth regressions only; not equivalence or held-out proof',
             'verdict':'NOT_PROVEN'}
    Executor._write(attempt/'regression-summary.json',summary)
    print(json.dumps(summary,indent=2))
    return 0 if observed_ok and result['accepted'] else 2


if __name__=='__main__':raise SystemExit(main())

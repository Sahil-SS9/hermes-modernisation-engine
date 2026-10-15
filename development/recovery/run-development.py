"""Fixed isolated development gate; no candidate execution grant API."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path('/home/kensei/projects/modernisation-benchmarks/control')
IMAGE='modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6'
p=argparse.ArgumentParser();p.add_argument('lane',choices=['unit','all','lint','validate','build','demo','checks']);a=p.parse_args()
base=['docker','run','--rm','--init','--pull=never','--name','modernise-dev-'+str(time.time_ns()),'--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=512m','--memory-swap=512m','--cpus=1','--user=65534:65534','--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777','--tmpfs','/work:rw,nosuid,nodev,size=128m,mode=1777','--env','HOME=/tmp','--env','HERMES_BUNDLED_PLUGINS=/tmp/empty','--env','PYTHONPATH=/source/src:/opt/hermes','--env','PYTHONDONTWRITEBYTECODE=1','--mount','type=bind,src=/home/kensei/repos/hermes-modernisation-engine,dst=/source,readonly,bind-recursive=disabled','--mount',f'type=bind,src={ROOT}/reference,dst=/reference,readonly,bind-recursive=disabled','--mount','type=bind,src=/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie,dst=/benchmark,readonly,bind-recursive=disabled','--workdir','/source',IMAGE]
if a.lane in ['unit','all']:
 roots=['tests/unit'] if a.lane=='unit' else ['tests']
 code="import pytest,xml.etree.ElementTree as E,json; status=pytest.main("+repr(roots+['-p','no:cacheprovider','-o','addopts=','--strict-markers','--junitxml=/tmp/result.xml','-ra'])+"); nodes=list(E.parse('/tmp/result.xml').getroot().iter('testcase')); print('COUNTS_JSON='+json.dumps({'tests':len(nodes),'failures':sum(n.find('failure') is not None for n in nodes),'errors':sum(n.find('error') is not None for n in nodes),'skipped':sum(n.find('skipped') is not None for n in nodes)})); raise SystemExit(status)"
 args=['python','-B','-c',code]
elif a.lane=='lint':args=['ruff','check','--no-cache','src','tests','scripts','__init__.py']
elif a.lane=='validate':args=['hermes','plugins','validate','/source','--json']
elif a.lane=='checks':args=['sh','scripts/checks.sh']
elif a.lane=='demo':args=['python','-B','scripts/demo_assessment.py']
else:args=['python','-B','scripts/build_artifact.py']
name=base[base.index('--name')+1]
try:r=subprocess.run(base+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150)
except subprocess.TimeoutExpired:
 subprocess.run(['docker','kill',name],capture_output=True,timeout=10);raise
state=subprocess.run(['docker','container','inspect',name],capture_output=True,text=True,timeout=10)
assert state.returncode!=0 and 'No such' in state.stderr
out=ROOT/'evidence'/('development-'+a.lane+'-'+str(time.time_ns()))
out.with_suffix('.log').write_bytes(r.stdout)
counts=[x.split('=',1)[1] for x in r.stdout.decode().splitlines() if x.startswith('COUNTS_JSON=')]
out.with_suffix('.json').write_text(json.dumps({'argv':base+args,'exit_code':r.returncode,'output_sha256':hashlib.sha256(r.stdout).hexdigest(),'container_removed':True,'counts':json.loads(counts[-1]) if counts else None},indent=2))
print(r.stdout.decode());print('EVIDENCE',out.with_suffix('.json'));raise SystemExit(r.returncode)

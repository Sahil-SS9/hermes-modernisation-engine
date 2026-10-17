import base64,hashlib,json,sys,xml.etree.ElementTree as E
import pytest
status=int(pytest.main(['tests/unit/test_dashboard_api.py','tests/security/test_ws_auth_fails_closed.py','-p','no:cacheprovider','-o','addopts=','--junitxml=/tmp/walkie-result.xml','-ra']))
sys.stdout.flush()
try:
    with open('/tmp/walkie-result.xml','rb') as stream:raw=stream.read(1048577)
except OSError:
    raw=b''
counts=None
if raw and len(raw)<=1048576:
    try:
        nodes=list(E.fromstring(raw).iter('testcase'))
        counts={'collected':len(nodes),'failures':sum(n.find('failure') is not None for n in nodes),'errors':sum(n.find('error') is not None for n in nodes),'skipped':sum(n.find('skipped') is not None for n in nodes)}
    except E.ParseError:
        counts=None
raw=raw[:1048576]
print('RUNNER_PYTEST_STATUS='+str(status))
print('RUNNER_COUNTS_JSON='+json.dumps(counts,sort_keys=True))
print('RUNNER_ENV_JSON='+json.dumps({'python':sys.version}))
print('RUNNER_JUNIT_BYTES='+str(len(raw)))
print('RUNNER_JUNIT_SHA256='+hashlib.sha256(raw).hexdigest())
print('RUNNER_JUNIT_BEGIN')
print(base64.b64encode(raw).decode())
print('RUNNER_JUNIT_END',flush=True)
raise SystemExit(0 if status==0 and counts=={'collected':20,'failures':0,'errors':0,'skipped':0} else 2)

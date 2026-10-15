"""Fixed-scope offline PR verification. No live host home or credentials mounted."""
import hashlib
import json
import subprocess
from pathlib import Path

IMAGE = 'modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6'
ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control')
BASE = ['docker','run','--rm','--init','--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=1g','--memory-swap=1g','--cpus=2','--user=65534:65534','--tmpfs','/tmp:rw,nosuid,nodev,size=256m,mode=1777','--env','HOME=/tmp','--env','HERMES_HOME=/tmp/hermes','--env','HERMES_BUNDLED_PLUGINS=/tmp/empty','--env','PYTHONDONTWRITEBYTECODE=1','--mount','type=bind,src=/home/kensei/repos/hermes-modernisation-engine/tests/host,dst=/probes,readonly,bind-recursive=disabled','--workdir','/opt/hermes']
SUITES = {
 'original-probe':['/probes/test_sdk_cli_namespace.py'],
 'focused':['tests/hermes_cli/test_plugin_cli_namespace.py','tests/hermes_cli/test_plugin_ownership_ledger.py','tests/hermes_cli/test_startup_plugin_gating.py','tests/hermes_cli/test_plugins.py','tests/hermes_cli/test_plugins_loader.py','tests/hermes_cli/test_plugin_manifest_v2.py','tests/hermes_cli/test_plugin_api_compat.py','tests/hermes_cli/test_plugin_cli_registration.py','tests/hermes_cli/test_plugin_validate.py','tests/hermes_cli/test_plugin_validate_private_imports.py','tests/hermes_cli/test_plugin_validate_locales.py'],
}
for name, files in SUITES.items():
    code = 'import pytest,xml.etree.ElementTree as E,json; status=pytest.main('+repr(files+['-p','no:cacheprovider','-o','addopts=','--junitxml=/tmp/result.xml','-ra'])+'); tree=E.parse("/tmp/result.xml"); nodes=list(tree.getroot().iter("testcase")); print("COUNTS_JSON="+json.dumps({"collected":len(nodes),"failures":sum(n.find("failure") is not None for n in nodes),"errors":sum(n.find("error") is not None for n in nodes),"skipped":sum(n.find("skipped") is not None for n in nodes)})); raise SystemExit(status)'
    command=BASE+['--name','modernise-fixed-' +name,IMAGE,'python','-B','-c',code]
    try:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','kill','modernise-fixed-' +name],capture_output=True,timeout=15)
        raise
    absence=subprocess.run(['docker','container','inspect','modernise-fixed-' +name],capture_output=True,text=True,timeout=10)
    assert absence.returncode != 0 and 'No such' in absence.stderr
    output=result.stdout
    log=ROOT/'evidence'/('validator-fixed-host-'+name+'.log')
    log.write_bytes(output)
    lines=[line for line in output.decode().splitlines() if line.startswith('COUNTS_JSON=')]
    counts=json.loads(lines[-1].split('=',1)[1]) if lines else None
    record={'pr':138686,'head_sha':'4539b09a730d6a97548b4d4102d10990033ead36','image':IMAGE,'argv':command,'exit_code':result.returncode,'counts':counts,'output_sha256':hashlib.sha256(output).hexdigest(),'container_removed':True,'scope':name}
    log.with_suffix('.json').write_text(json.dumps(record,indent=2))
    print(output.decode(),flush=True)
    print('EVIDENCE',log,flush=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

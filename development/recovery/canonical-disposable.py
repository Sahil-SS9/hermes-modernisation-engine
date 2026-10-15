"""Run native canonical tests in disposable container-owned storage."""
import json
import hashlib
import subprocess
from pathlib import Path

IMAGE='modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6'
code='''import os,shutil,subprocess
from pathlib import Path
root=Path('/work/hermes')
shutil.copytree('/opt/hermes',root,ignore=shutil.ignore_patterns('.venv','__pycache__','.git'))
(root/'.venv').symlink_to('/opt/hermes/.venv',target_is_directory=True)
os.chdir(root)
env=dict(os.environ,HERMES_PYTHON='/opt/hermes/.venv/bin/python')
result=subprocess.run(['bash','scripts/run_tests.sh','tests/hermes_cli/test_plugin_validate.py','tests/hermes_cli/test_plugin_validate_private_imports.py','tests/hermes_cli/test_plugin_validate_locales.py','-j','2','-p','no:cacheprovider'],env=env)
assert (root/'test_durations.json').is_file(), 'Timing cache was not saved in disposable work root'
raise SystemExit(result.returncode)
'''
command=['docker','run','--rm','--init','--pull=never','--name','modernise-disposable-canonical','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=1g','--memory-swap=1g','--cpus=2','--user=65534:65534','--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777','--tmpfs','/var/tmp:rw,nosuid,nodev,size=128m,mode=1777','--tmpfs','/work:rw,nosuid,nodev,size=512m,mode=1777','--env','HOME=/tmp',IMAGE,'python','-B','-c',code]
try:
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150)
except subprocess.TimeoutExpired:
    subprocess.run(['docker','kill','modernise-disposable-canonical'],capture_output=True,timeout=15)
    raise
absent=subprocess.run(['docker','container','inspect','modernise-disposable-canonical'],capture_output=True,text=True,timeout=10)
assert absent.returncode!=0 and 'No such' in absent.stderr
root=Path('/home/kensei/projects/modernisation-benchmarks/control/evidence')
(root/'canonical-disposable.log').write_bytes(result.stdout)
(root/'canonical-disposable.json').write_text(json.dumps({'argv':command,'exit_code':result.returncode,'output_sha256':hashlib.sha256(result.stdout).hexdigest(),'container_removed':True},indent=2))
print(result.stdout.decode())
raise SystemExit(result.returncode)

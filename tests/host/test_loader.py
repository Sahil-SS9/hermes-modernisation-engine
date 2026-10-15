"""Native loader and command smoke. Requires the pinned PR host sandbox."""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/source')


def installed_home(tmp_path):
    assert (ROOT/'plugin.yaml').is_file(), 'Native plugin manifest not implemented'
    assert (ROOT/'__init__.py').is_file(), 'Native registration entrypoint not implemented'
    home = tmp_path/'home'
    target = home/'plugins'/'modernisation-engine'
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('.git', '__pycache__'))
    (home/'config.yaml').write_text('plugins:\n  enabled:\n    - modernisation-engine\n')
    environment = dict(os.environ, HERMES_HOME=str(home), HOME=str(home), HERMES_BUNDLED_PLUGINS=str(home/'empty'), HERMES_ENABLE_PROJECT_PLUGINS='0')
    return home, environment


def test_native_cli_status_is_honest_and_run_denied(tmp_path):
    home, environment = installed_home(tmp_path)
    command = ['/opt/hermes/.venv/bin/hermes', 'modernise']
    status = subprocess.run(command+['status'], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert status.returncode == 0, status.stdout+status.stderr
    result = json.loads(status.stdout)
    assert result['implementation_status'] == 'PHASE_0_ONLY'
    assert result['execution_available'] is False
    assert result['missing_evidence']
    denied = subprocess.run(command+['run', '--job', 'forged'], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert denied.returncode == 2
    assert json.loads(denied.stdout)['error'] == 'EXECUTION_UNAVAILABLE'
    refused = subprocess.run(command+['run', '--job', 'forged', '--approved'], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert refused.returncode != 0
    assert 'unrecognized arguments' in refused.stderr or 'EXECUTION_UNAVAILABLE' in refused.stdout


def test_real_registry_slash_reload_and_unload(tmp_path):
    home, environment = installed_home(tmp_path)
    code = '''import json
from hermes_cli.plugins import discover_plugins,get_plugin_manager,get_plugin_command_handler
from tools.registry import registry
discover_plugins()
m=get_plugin_manager()
p=next(x for x in m.list_plugins() if x['key']=='modernisation-engine')
assert p['enabled'] and not p['error'],p
result=json.loads(registry.dispatch('modernise_status',{},scope=m.scope_key))
assert result['implementation_status']=='PHASE_0_ONLY'
slash=get_plugin_command_handler('modernise')
assert json.loads(slash('status'))['execution_available'] is False
assert json.loads(slash('run --job forged --approved'))['error']=='EXECUTION_UNAVAILABLE'
m.discover_and_load(force=True)
assert json.loads(registry.dispatch('modernise_status',{},scope=m.scope_key))['execution_available'] is False
assert m.unload('modernisation-engine')
assert registry.get_entry('modernise_status',scope=m.scope_key) is None
print('NATIVE_REGISTRY_SLASH_HANDLER_RELOAD_UNLOAD_OK')
'''
    result = subprocess.run(['python','-B','-c',code],cwd=home,env=environment,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'NATIVE_REGISTRY_SLASH_HANDLER_RELOAD_UNLOAD_OK' in result.stdout

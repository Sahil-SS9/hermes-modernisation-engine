"""Native loader and command smoke. Requires the pinned PR host sandbox."""

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/source")


def installed_home(tmp_path):
    assert (ROOT / "plugin.yaml").is_file(), "Native plugin manifest not implemented"
    assert (ROOT / "__init__.py").is_file(), (
        "Native registration entrypoint not implemented"
    )
    home = tmp_path / "home"
    target = home / "plugins" / "modernisation-engine"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    (home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - modernisation-engine\n"
    )
    environment = dict(
        os.environ,
        HERMES_HOME=str(home),
        HOME=str(home),
        HERMES_BUNDLED_PLUGINS=str(home / "empty"),
        HERMES_ENABLE_PROJECT_PLUGINS="0",
    )
    return home, environment


def test_native_cli_status_is_honest_and_run_denied(tmp_path):
    home, environment = installed_home(tmp_path)
    command = ["/opt/hermes/.venv/bin/hermes", "modernise"]
    status = subprocess.run(
        command + ["status"],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert status.returncode == 0, status.stdout + status.stderr
    result = json.loads(status.stdout)
    assert result["implementation_status"] == "READ_ONLY_PREVIEW"
    assert result["execution_available"] is False
    assert result["missing_evidence"]
    denied = subprocess.run(
        command + ["run", "--job", "forged"],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert denied.returncode == 2
    assert json.loads(denied.stdout)["error"] == "EXECUTION_UNAVAILABLE"
    refused = subprocess.run(
        command + ["run", "--job", "forged", "--approved"],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert refused.returncode != 0
    assert (
        "unrecognized arguments" in refused.stderr
        or "EXECUTION_UNAVAILABLE" in refused.stdout
    )


def test_native_assess_plan_report_journey(tmp_path):
    home, environment = installed_home(tmp_path)
    repo = tmp_path / "example"
    repo.mkdir()
    (repo / "a.py").write_text("def double(x):\n    return x*2\n")

    def call(*arguments):
        result = subprocess.run(
            ["/opt/hermes/.venv/bin/hermes", "modernise", *arguments],
            cwd=home,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    job = call(
        "assess",
        "--repo",
        str(repo),
        "--goal",
        "upgrade",
        "--request-id",
        "native-test",
    )
    assert job["assessment"]["file_count"] == 1
    assert (
        call(
            "inventory", "--job", job["job_id"], "--section", "symbols", "--page", "0"
        )["items"][0]["name"]
        == "double"
    )
    planned = call("plan", "--job", job["job_id"], "--revision", "0")
    assert planned["state"] == "BASELINE_AUTHORITY_REQUIRED"
    assert call("compare", "--job", job["job_id"])["verdict"] == "NOT_PROVEN"
    assert "NOT_PROVEN" in call("report", "--job", job["job_id"])["text"]
    assert call("status", "--job", job["job_id"])["revision"] == 1
    assert (repo / "a.py").read_text() == "def double(x):\n    return x*2\n"


def test_real_registry_slash_reload_and_unload(tmp_path):
    home, environment = installed_home(tmp_path)
    code = """import json
from hermes_cli.plugins import discover_plugins,get_plugin_manager,get_plugin_command_handler
from tools.registry import registry
discover_plugins()
m=get_plugin_manager()
p=next(x for x in m.list_plugins() if x['key']=='modernisation-engine')
assert p['enabled'] and not p['error'],p
result=json.loads(registry.dispatch('modernise_status',{},scope=m.scope_key))
assert result['implementation_status']=='READ_ONLY_PREVIEW'
slash=get_plugin_command_handler('modernise')
assert json.loads(slash('status'))['execution_available'] is False
assert json.loads(slash('run --job forged --approved'))['error']=='EXECUTION_UNAVAILABLE'
m.discover_and_load(force=True)
assert json.loads(registry.dispatch('modernise_status',{},scope=m.scope_key))['execution_available'] is False
assert m.unload('modernisation-engine')
for name in ('status','assess','inventory','plan','compare','report'):
    assert registry.get_entry('modernise_'+name,scope=m.scope_key) is None
print('NATIVE_REGISTRY_SLASH_HANDLER_RELOAD_UNLOAD_OK')
"""
    result = subprocess.run(
        ["python", "-B", "-c", code],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NATIVE_REGISTRY_SLASH_HANDLER_RELOAD_UNLOAD_OK" in result.stdout


def test_contract_registration_reaches_native_cli_tool_and_slash(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("owned_contract_fixture", ROOT / "tests/unit/test_behaviour_contract.py")
    assert spec is not None and spec.loader is not None
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    _, _, contract = fixture.contract_fixture(tmp_path)
    home, environment = installed_home(tmp_path)
    command = ["/opt/hermes/.venv/bin/hermes", "modernise"]
    source = str(tmp_path / "legacy")
    assessed = subprocess.run(command + ["assess", "--repo", source, "--goal", "fixture", "--request-id", "native-contract"], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert assessed.returncode == 0, assessed.stdout + assessed.stderr
    jid = json.loads(assessed.stdout)["job_id"]
    registered = subprocess.run(command + ["contract", "--job", jid, "--revision", "0", "--contract", json.dumps(contract)], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert registered.returncode == 0, registered.stdout + registered.stderr
    assert json.loads(registered.stdout)["behaviour_contract"]["review_state"] == "unreviewed"
    code = """import json,shlex
from hermes_cli.plugins import discover_plugins,get_plugin_manager,get_plugin_command_handler
from tools.registry import registry
discover_plugins(); m=get_plugin_manager()
args=json.loads(PAYLOAD)
a=json.loads(registry.dispatch('modernise_contract',args,scope=m.scope_key))
assert a['behaviour_contract']['review_state']=='unreviewed',a
slash=get_plugin_command_handler('modernise')
command='contract --job '+shlex.quote(args['job'])+' --revision 0 --contract '+shlex.quote(json.dumps(args['contract']))
b=json.loads(slash(command))
assert b==a,(a,b)
malformed=json.loads(slash('contract --job '+args['job']+' --revision 1 --contract '+shlex.quote('{"schema_version":1,"schema_version":2}')))
assert malformed['error']=='INVALID_ARGUMENTS',malformed
assert m.unload('modernisation-engine')
assert registry.get_entry('modernise_contract',scope=m.scope_key) is None
print('NATIVE_CONTRACT_CLI_TOOL_SLASH_OK')
""".replace("PAYLOAD", repr(json.dumps({"job": jid, "revision": 0, "contract": contract})))
    result = subprocess.run(["python", "-B", "-c", code], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NATIVE_CONTRACT_CLI_TOOL_SLASH_OK" in result.stdout

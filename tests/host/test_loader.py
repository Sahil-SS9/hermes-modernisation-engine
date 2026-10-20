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
    described = subprocess.run(command + ["schema", "--name", "migration-job-v1"], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert described.returncode == 0, described.stdout + described.stderr
    assert json.loads(described.stdout)["schema"]["properties"]["kind"]["const"] == "MigrationJob"
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
descriptor=json.loads(registry.dispatch('modernise_schema',{'name':'migration-job-v1'},scope=m.scope_key))
assert descriptor['kind']=='SchemaDescriptor' and not descriptor['execution_performed'],descriptor
assert json.loads(slash('schema --name migration-job-v1'))==descriptor
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
request={'job':args['job'],'phase':'baseline','actor':'fixture_owner','request_id':'native_prepare','timeout_seconds':20,'output_limit_bytes':65536}
draft=json.loads(registry.dispatch('modernise_prepare',request,scope=m.scope_key))
assert draft.get('state')=='PREPARED' and not draft['permission_granted'],draft
listed=json.loads(slash('attempts --job '+args['job']))
assert listed['attempts']==[draft],listed
assert m.unload('modernisation-engine')
assert registry.get_entry('modernise_contract',scope=m.scope_key) is None
print('NATIVE_CONTRACT_CLI_TOOL_SLASH_OK')
""".replace("PAYLOAD", repr(json.dumps({"job": jid, "revision": 0, "contract": contract})))
    result = subprocess.run(["python", "-B", "-c", code], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NATIVE_CONTRACT_CLI_TOOL_SLASH_OK" in result.stdout
    prepared = subprocess.run(command + ["prepare", "--job", jid, "--phase", "baseline", "--actor", "fixture_owner", "--request-id", "native_prepare", "--timeout-seconds", "20", "--output-limit-bytes", "65536"], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    planned = json.loads(prepared.stdout)
    assert planned["state"] == "PREPARED" and not planned["permission_granted"]
    listed = subprocess.run(command + ["attempts", "--job", jid], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    assert json.loads(listed.stdout)["attempts"] == [planned]


def test_real_native_review_cli_and_dispatch_use_the_trusted_operator_setting(tmp_path):
    import base64
    import importlib.util
    import time
    import uuid

    from hermes_modernisation.approvals import canonical

    spec = importlib.util.spec_from_file_location("configured_review_fixture", ROOT / "tests/unit/test_review_requests.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    _, _, contract, key, _, config = fixture.configured_fixture(tmp_path)
    home, environment = installed_home(tmp_path)
    (home / "config.yaml").write_text("plugins:\n  enabled: [modernisation-engine]\n  entries:\n    modernisation-engine:\n      settings:\n        operator_config: " + str(config) + "\n")

    def call(*args):
        result = subprocess.run(["/opt/hermes/.venv/bin/hermes", "modernise", *args], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    jid = call("assess", "--repo", str(tmp_path / "legacy"), "--goal", "Native review fixture", "--request-id", "native_review")["job_id"]
    call("contract", "--job", jid, "--revision", "0", "--contract", json.dumps(contract))
    draft = call("review_request", "--job", jid, "--purpose", "contract", "--actor", "fixture_owner")
    assert draft["permission_granted"] is False
    body = {"schema_version": 1, "decision": draft["decision"], "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
    grant = {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}
    accepted = call("review", "--job", jid, "--grant", json.dumps(grant))
    assert accepted["contract_review"]["authenticated"] is True
    prepared = call("prepare", "--job", jid, "--phase", "baseline", "--actor", "fixture_owner", "--request-id", "native_control", "--timeout-seconds", "20", "--output-limit-bytes", "65536")
    control = call("control_request", "--job", jid, "--attempt", prepared["attempt_id"], "--purpose", "recover", "--actor", "fixture_owner")
    assert control["decision"]["kind"] == "ControlDecision" and not control["permission_granted"]
    code = """import json,shlex
from hermes_cli.plugins import discover_plugins,get_plugin_manager,get_plugin_command_handler
from tools.registry import registry
from plugins.plugin_storage import plugin_data_dir
discover_plugins(); manager=get_plugin_manager()
args=json.loads(PAYLOAD)
forged=json.loads(registry.dispatch('modernise_review',{'job':args['job'],'grant':{'approved':True}},scope=manager.scope_key))
assert forged['error']=='INVALID_REQUEST' and not forged['execution_performed'],forged
request=json.loads(registry.dispatch('modernise_review_request',{'job':args['job'],'purpose':'contract','actor':'fixture_owner'},scope=manager.scope_key))
assert not request['permission_granted'],request
prepared=json.loads(registry.dispatch('modernise_prepare',{'job':args['job'],'phase':'baseline','actor':'fixture_owner','request_id':'native_control','timeout_seconds':20,'output_limit_bytes':65536},scope=manager.scope_key))
control=json.loads(registry.dispatch('modernise_control_request',{'job':args['job'],'attempt':prepared['attempt_id'],'purpose':'recover','actor':'fixture_owner'},scope=manager.scope_key))
assert control['decision']['kind']=='ControlDecision' and not control['permission_granted'],control
slash=get_plugin_command_handler('modernise')
for action in ('cancel','recover','recover_build'):
    refused=json.loads(slash(action+' --job '+args['job']+' --attempt '+prepared['attempt_id']+' --grant '+shlex.quote(json.dumps({'approved':True}))))
    assert refused['error']=='INVALID_REQUEST' and not refused['execution_performed'],refused
replayed=json.loads(slash('review --job '+args['job']+' --grant '+shlex.quote(json.dumps(args['grant']))))
assert replayed['error']=='INVALID_REQUEST' and not replayed['execution_performed'],replayed
assert json.loads(slash('status --job '+args['job']))['contract_review']['authenticated'] is True
assert manager.unload('modernisation-engine')
for name in ('review','review_request','proposal','build','run','resume','control_request','cancel','recover','recover_build','schema'):
    assert registry.get_entry('modernise_'+name,scope=manager.scope_key) is None,name
print('NATIVE_CONFIGURED_REVIEW_CLI_TOOL_SLASH_OK')
""".replace("PAYLOAD", repr(json.dumps({"job": jid, "grant": grant})))
    result = subprocess.run(["python", "-B", "-c", code], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NATIVE_CONFIGURED_REVIEW_CLI_TOOL_SLASH_OK" in result.stdout

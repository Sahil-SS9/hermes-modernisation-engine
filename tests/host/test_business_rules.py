"""Actual isolated native CLI, registered tool and slash rule contract smoke."""

import json
import subprocess

from test_loader import installed_home


def test_native_business_rule_schema_and_inventory_share_the_public_service(tmp_path):
    home, environment = installed_home(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("def checked(value):\n    assert value >= 0\n    return value\n")
    command = ["/opt/hermes/.venv/bin/hermes", "modernise"]

    def call(*arguments):
        result = subprocess.run(command + list(arguments), cwd=home, env=environment, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    descriptor = call("schema", "--name", "business-rule-v1")
    assert descriptor["schema"]["properties"]["kind"]["const"] == "BusinessRule"
    job = call("assess", "--repo", str(source), "--goal", "Rules fixture", "--request-id", "native_rules")
    page = call("inventory", "--job", job["job_id"], "--section", "rules", "--page", "0")
    assert page["items"][0]["kind"] == "BusinessRule"
    assert page["items"][0]["owner_reviewed"] is False
    code = """import json
from hermes_cli.plugins import discover_plugins,get_plugin_manager,get_plugin_command_handler
from tools.registry import registry
discover_plugins(); manager=get_plugin_manager()
expected=json.loads(EXPECTED)
args=json.loads(ARGUMENTS)
descriptor=json.loads(registry.dispatch('modernise_schema',{'name':'business-rule-v1'},scope=manager.scope_key))
assert descriptor['schema']['properties']['kind']['const']=='BusinessRule',descriptor
assert json.loads(registry.dispatch('modernise_inventory',args,scope=manager.scope_key))==expected
slash=get_plugin_command_handler('modernise')
assert json.loads(slash('schema --name business-rule-v1'))==descriptor
assert json.loads(slash('inventory --job '+args['job']+' --section rules --page 0'))==expected
assert expected['items'][0]['coverage_status']=='unverified'
assert manager.unload('modernisation-engine')
for name in ('schema','inventory'):
    assert registry.get_entry('modernise_'+name,scope=manager.scope_key) is None
print('NATIVE_BUSINESS_RULE_CONTRACT_OK')
""".replace("EXPECTED", repr(json.dumps(page))).replace("ARGUMENTS", repr(json.dumps({"job": job["job_id"], "section": "rules", "page": 0})))
    result = subprocess.run(["python", "-B", "-c", code], cwd=home, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NATIVE_BUSINESS_RULE_CONTRACT_OK" in result.stdout

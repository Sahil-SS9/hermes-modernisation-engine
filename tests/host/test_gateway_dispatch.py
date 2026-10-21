"""Actual gateway slash dispatch on the pinned isolated host.

The host image carries the real TUI gateway.  This probe uses its registered
JSON-RPC dispatcher (the same ``command.dispatch`` method the desktop gateway
serves) rather than a re-implementation or a fake command registry.  A plugin
slash handler is not authority: the unconfigured ``run`` route must refuse even
when the handler is called directly.
"""

import json
import subprocess

from test_loader import installed_home

PROBE = r"""
import json
import sys
from tui_gateway.server import dispatch
from hermes_cli.plugins import get_plugin_command_handler


def call(request_id, name, arg):
    dispatch({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "command.dispatch",
        "params": {"name": name, "arg": arg},
    })


raw = get_plugin_command_handler("modernise")("run --job forged")
if not isinstance(raw, str):
    raw = json.dumps(raw)
print("PROBE_RAW=" + raw, file=sys.stderr, flush=True)

call("status", "modernise", "status")
call("run", "modernise", "run --job forged")
call("unknown", "definitely-not-a-command", "")
"""


def _responses(stdout):
    found = {}
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") in {"status", "run", "unknown"}:
            found[message["id"]] = message
    return found


def test_gateway_slash_dispatch_and_raw_registry_refusal(tmp_path):
    home, environment = installed_home(tmp_path)
    completed = subprocess.run(
        ["/opt/hermes/.venv/bin/python", "-B", "-c", PROBE],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    responses = _responses(completed.stdout)
    assert set(responses) == {"status", "run", "unknown"}, completed.stdout

    status = responses["status"]
    assert status["result"]["type"] == "plugin"
    described = json.loads(status["result"]["output"])
    assert described["implementation_status"] == "READ_ONLY_PREVIEW"
    assert described["execution_available"] is False

    for key in ("run", "unknown"):
        assert responses[key].get("result", {}).get("output") or responses[key].get("error")
    run_output = json.loads(responses["run"]["result"]["output"])
    assert run_output["error"] == "EXECUTION_UNAVAILABLE"
    assert run_output["execution_performed"] is False
    assert responses["unknown"]["error"]["code"] == 4018

    marker = [
        line for line in completed.stderr.splitlines() if line.startswith("PROBE_RAW=")
    ]
    assert marker, completed.stderr
    raw_output = json.loads(marker[-1].split("=", 1)[1])
    assert raw_output["error"] == "EXECUTION_UNAVAILABLE"
    assert raw_output["execution_performed"] is False

"""Real rootless collector boundary probe, FIXTURE AUTHORITY ONLY.

Run with the already approved control/operator-env Python, not host pytest.
No real owner key, project, provider, daemon configuration or install is used.
All evidence is retained in a fresh private namespace; no directory cleanup.
This is not native product-run, staging/recovery or final release acceptance.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hermes_modernisation.approvals import AuthorityDenied, ExternalAuthority, canonical
from hermes_modernisation.baseline import capture, make_inputs
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.service import Engine

APP = '''import json, sys

def calculate(item):
    value = item.get("value") if type(item) is dict else None
    if type(value) is not int:
        return {"error": "invalid"}
    return {"value": VALUE_EXPRESSION}

request = json.load(sys.stdin)
json.dump({"schema_version": 1, "results": [
    {"id": item["id"], "output": calculate(item["input"])}
    for item in request["cases"]
]}, sys.stdout)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-parent", type=Path, required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    parent = args.work_parent
    if not parent.is_absolute() or parent.resolve() != parent:
        raise SystemExit("An unambiguous absolute owned fixture parent is required")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = parent.stat()
    assert info.st_uid == os.geteuid() and not stat.S_IMODE(info.st_mode) & 0o077
    root = parent / ("capture-" + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    authority_root = root / "authority"
    authority_root.mkdir(mode=0o700)
    key = Ed25519PrivateKey.generate()
    authority = ExternalAuthority({"fixture_owner": key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)}, authority_root / "claims.sqlite")
    baseline = root / "baseline"
    baseline.mkdir(mode=0o755)
    raw = APP.replace("VALUE_EXPRESSION", "value * 2").encode()
    (baseline / "app.py").write_bytes(raw)
    engine = Engine(root / "state", profile="fixture")
    job = engine.invoke("assess", {"repo": str(baseline), "goal": "Owned finite JSON response fixture", "request_id": "owned_fixture"})
    cases = [{"id": "fresh_" + str(i), "kind": "fresh", "input": {"value": i}, "expected": {"value": i * 2}, "rule_ids": ["double"]} for i in range(1, 11)]
    for cid, kind, value in [("zero", "boundary", 0), ("negative", "boundary", -7), ("string", "malformed", "bad"), ("boolean", "malformed", True), ("null", "malformed", None)]:
        expected = {"value": value * 2} if type(value) is int else {"error": "invalid"}
        cases.append({"id": cid, "kind": kind, "input": {"value": value}, "expected": expected, "rule_ids": ["double"]})
    contract = {
        "schema_version": 1, "kind": "BehaviourContract", "scope": "owned_finite_json_responses", "track": "uplift",
        "source_digest": job["assessment"]["source_digest"], "adapter": "json-batch-v1",
        "runtimes": {phase: {"image": args.image, "argv": ["python", "-B", "/source/app.py"]} for phase in ("baseline", "candidate")},
        "allowed_paths": ["app.py"], "seed": 41,
        "rules": [{"id": "double", "text": "Double integers and reject other input types", "source_refs": [{"path": "app.py", "line_start": 3, "line_end": 7, "sha256": hashlib.sha256(raw).hexdigest()}], "case_ids": [case["id"] for case in cases]}],
        "cases": cases, "normalizations": [], "planned_differences": [],
    }
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    oracle = root / "private-oracle.json"
    oracle.write_bytes(dumps(contract))
    oracle.chmod(0o600)
    oracle_sha = hashlib.sha256(oracle.read_bytes()).hexdigest()
    marker = root / "private-marker.txt"
    marker_bytes = ("PRIVATE_FIXTURE_CANARY_" + uuid.uuid4().hex).encode()
    marker.write_bytes(marker_bytes)
    marker.chmod(0o600)
    work = root / "executor"
    audits = []
    captures = []

    def runtime_audit(label, detail):
        if label != "START_REQUESTED":
            return
        inspection = subprocess.run(["docker", "inspect", detail["container_id"]], check=True, capture_output=True, text=True, timeout=15)
        actual = json.loads(inspection.stdout)[0]
        host = actual["HostConfig"]
        assert host["NetworkMode"] == "none" and host["ReadonlyRootfs"]
        assert host["PidsLimit"] == 64 and host["Memory"] == 536870912
        assert actual["Config"]["User"] == "65534:65534"
        binds = [mount for mount in actual["Mounts"] if mount["Type"] == "bind"]
        assert len(binds) == 1 and binds[0]["Destination"] == "/source" and binds[0]["RW"] is False
        assert str(oracle) != binds[0]["Source"] and str(marker) != binds[0]["Source"]
        names = [item.split("=", 1)[0] for item in actual["Config"]["Env"]]
        assert not any(any(token in name.upper() for token in ("API_KEY", "TOKEN", "PASSWORD", "SECRET")) for name in names)
        audits.append({"container_id": actual["Id"], "network": "none", "source_readonly": True, "oracle_or_control_mount": False, "provider_environment_names": False})

    def run(label, source, phase, *, prepared=None, lease=None):
        aid = prepared["attempt_id"] if prepared else uuid.uuid4().hex
        payload = make_inputs(contract, aid)

        def checkpoint(name, details):
            runtime_audit(name, details)
            if lease is not None:
                engine.store.checkpoint_attempt(job["job_id"], aid, lease, name, details)

        executor = Executor(authority, work, args.image, profile="fixture", phase=phase, input_data=payload, checkpoint=checkpoint)
        digest = snapshot(source)["digest"]
        operation = prepared["operation"] if prepared else {
            "schema_version": 1, "job_id": job["job_id"], "attempt_id": aid, "actor": "fixture_owner", "profile": "fixture",
            "source_digest": digest, "candidate_digest": digest, "oracle_digest": oracle_sha,
            "image_digest": args.image.split("@sha256:")[-1], "argv": contract["runtimes"][phase]["argv"],
            "read_roots": ["/source"], "write_roots": ["/tmp", "/work"], "network": "none", "timeout_seconds": 20, "output_limit_bytes": 65536,
        }
        if prepared is None:
            operation["environment_digest"] = hashlib.sha256(dumps(executor.environment(operation))).hexdigest()
        body = {"schema_version": 1, "operation": operation, "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
        grant = {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}
        rejection = None
        result = None
        try:
            result = capture(executor, grant, operation, source, oracle, contract)
        except ContractError as error:
            rejection = str(error)
        cleanup = json.loads((work / aid / "cleanup.json").read_text())
        assert cleanup["removed"] is True
        cid = json.loads((work / aid / "container.json").read_text())["container_id"]
        retired = subprocess.run(["docker", "container", "inspect", cid], capture_output=True, text=True, timeout=15)
        assert retired.returncode != 0 and "No such" in retired.stderr
        assert snapshot(source)["digest"] == digest
        try:
            authority.claim(grant, operation)
        except AuthorityDenied:
            pass
        else:
            raise AssertionError("Spent fixture authority replayed")
        row = {"label": label, "attempt_id": aid, "container_id": cid, "removed_readback": True, "source_unchanged": True, "replay_refused": True, "rejection": rejection}
        if result:
            row["evaluation"] = {key: result["evaluation"][key] for key in ("expected", "collected", "passed", "failed", "errors", "skipped", "provenance", "verdict")}
        captures.append(row)
        return result

    prepared = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "fixture_baseline", "timeout_seconds": 20, "output_limit_bytes": 65536})
    lease = engine.store.claim_attempt(job["job_id"], prepared["attempt_id"], "fixture_worker")
    original = run("original", baseline, "baseline", prepared=prepared, lease=lease)
    assert original and original["evaluation"]["passed"] == len(cases)
    journal = engine.store.attempts_for(job["job_id"])[0]
    assert [item["label"] for item in journal["checkpoints"]] == ["AUTHORITY_CLAIMED", "START_REQUESTED", "COLLECTED", "CLEANUP_VERIFIED"]
    engine.store.stop_attempt(job["job_id"], prepared["attempt_id"], lease, "CANCELLED", "Fixture collector scope complete; no product acceptance invoked")
    sources = {
        "good_upgrade": APP.replace("VALUE_EXPRESSION", "value + value"),
        "behavioural_mutant": APP.replace("VALUE_EXPRESSION", "value * 3"),
        "forged_junit": 'print(\'<testsuite tests="15" failures="0"/>\')\n',
        "private_file_spy": "from pathlib import Path\ntry:\n    leaked=Path(" + repr(str(marker)) + ").read_bytes()\nexcept OSError:\n    pass\nelse:\n    print(leaked.decode()); raise SystemExit(44)\n" + APP.replace("VALUE_EXPRESSION", "value * 2"),
    }
    for label, program in sources.items():
        source = root / label
        source.mkdir(mode=0o755)
        (source / "app.py").write_text(program)
        result = run(label, source, "candidate")
        if label in {"good_upgrade", "private_file_spy"}:
            assert result and result["evaluation"]["passed"] == len(cases)
        elif label == "behavioural_mutant":
            assert result and result["evaluation"]["failed"] > 0
        else:
            assert result is None and captures[-1]["rejection"]
    assert marker.read_bytes() == marker_bytes and hashlib.sha256(oracle.read_bytes()).hexdigest() == oracle_sha
    assert not any(marker_bytes in path.read_bytes() for path in work.glob("*/output.bin"))
    with sqlite3.connect(authority.ledger) as database:
        claims = database.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    assert claims == len(captures) == len(audits)
    report = {"schema_version": 1, "status": "FIXTURE_BOUNDARY_PASSED", "fixture_authority_only": True, "real_owner_approval_used": False, "native_product_run_proven": False, "engine_staging_or_recovery_proven": False, "engine_core_digest": snapshot(Path(__file__).resolve().parents[1] / "src/hermes_modernisation")["digest"], "oracle_sha256": oracle_sha, "expected_cases_per_capture": len(cases), "captures": captures, "runtime_audits": audits, "authority_claims": claims, "protected_marker_unchanged_and_not_in_output": True, "outer_verdict": "NOT_PROVEN", "limits": ["finite owned JSON response fixture only", "not a real owner-approved application trial", "not full native workflow, staging or recovery", "not final review or release acceptance"]}
    target = root / "result.json"
    target.write_bytes(dumps(report))
    target.chmod(0o600)
    print(json.dumps({"status": report["status"], "result": str(target), "captures": len(captures), "expected_cases_per_capture": len(cases), "real_owner_approval_used": False}))


if __name__ == "__main__":
    main()

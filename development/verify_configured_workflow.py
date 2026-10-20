"""Exercise the configured public Engine journey on owned fixture code only.

No real owner key/permission or real project is used. This driver does not
install or alter Hermes. Actual native-host routes are a separate gate.
"""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hermes_modernisation.approvals import canonical
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import dumps
from hermes_modernisation.service import Engine
from verify_protected_capture import APP


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-parent", required=True, type=Path)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    parent = args.work_parent
    assert parent.is_absolute() and parent.resolve() == parent and parent.is_dir()
    root = parent / ("workflow-" + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    original = root / "original"
    original.mkdir(mode=0o755)
    raw = APP.replace("VALUE_EXPRESSION", "value * 2").encode()
    (original / "app.py").write_bytes(raw)
    key = Ed25519PrivateKey.generate()
    config = root / "operator.json"
    Executor._write(config, {"schema_version": 1, "profile": "fixture", "workspace": str(workspace), "public_keys": {"fixture_owner": base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()}, "images": [args.image]})
    engine = Engine(root / "private", profile="fixture", operator_config=config)
    job = engine.invoke("assess", {"repo": str(original), "goal": "Owned configured protected-response journey", "request_id": "fixture_journey"})
    jid = job["job_id"]
    cases = [{"id": "fresh_" + str(i), "kind": "fresh", "input": {"value": i}, "expected": {"value": i * 2}, "rule_ids": ["double"]} for i in range(1, 11)]
    for cid, kind, value in [("zero", "boundary", 0), ("negative", "boundary", -7), ("string", "malformed", "bad"), ("boolean", "malformed", True), ("null", "malformed", None)]:
        cases.append({"id": cid, "kind": kind, "input": {"value": value}, "expected": {"value": value * 2} if type(value) is int else {"error": "invalid"}, "rule_ids": ["double"]})
    contract = {"schema_version": 1, "kind": "BehaviourContract", "scope": "owned_configured_json_responses", "track": "uplift", "source_digest": job["assessment"]["source_digest"], "adapter": "json-batch-v1", "runtimes": {phase: {"image": args.image, "argv": ["python", "-B", "/source/app.py"]} for phase in ("baseline", "candidate")}, "allowed_paths": ["app.py"], "seed": 41, "rules": [{"id": "double", "text": "Double integers, reject other types", "source_refs": [{"path": "app.py", "line_start": 3, "line_end": 7, "sha256": hashlib.sha256(raw).hexdigest()}], "case_ids": [case["id"] for case in cases]}], "cases": cases, "normalizations": [], "planned_differences": []}
    engine.invoke("contract", {"job": jid, "revision": 0, "contract": contract})

    def sign(field, value):
        body = {"schema_version": 1, field: value, "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
        return {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}

    def review(purpose):
        decision = engine.invoke("review_request", {"job": jid, "actor": "fixture_owner", "purpose": purpose})["decision"]
        return engine.invoke("review", {"job": jid, "grant": sign("decision", decision)})

    def run(phase):
        prepared = engine.invoke("prepare", {"job": jid, "phase": phase, "actor": "fixture_owner", "request_id": phase + "_request", "timeout_seconds": 20, "output_limit_bytes": 65536})
        grant = sign("operation", prepared["operation"])
        result = engine.invoke("run", {"job": jid, "attempt": prepared["attempt_id"], "grant": grant})
        attempts = engine.invoke("attempts", {"job": jid})["attempts"]
        saved = next(item for item in attempts if item["attempt_id"] == prepared["attempt_id"])
        assert saved["state"] == "COMPLETED", saved
        assert [item["label"] for item in saved["checkpoints"]] == ["AUTHORITY_CLAIMED", "START_REQUESTED", "COLLECTED", "CLEANUP_VERIFIED"]
        return result

    review("contract")
    baseline = run("baseline")
    assert baseline["state"] == "BASELINED" and baseline["baseline_ref"]["passed"] == len(cases), baseline
    proposal = {"schema_version": 1, "source_digest": job["assessment"]["source_digest"], "goal": job["goal"], "changes": [{"path": "app.py", "before_sha256": hashlib.sha256(raw).hexdigest(), "replacement": APP.replace("VALUE_EXPRESSION", "value + value")}], "allowed_paths": ["app.py"], "planned_differences": []}
    engine.invoke("proposal", {"job": jid, "revision": baseline["revision"], "proposal": proposal})
    review("migration")
    built = engine.invoke("build", {"job": jid})
    assert built["state"] == "CANDIDATE_BUILT", built
    candidate = Path(built["candidate_ref"]["path"])
    assert candidate.is_relative_to(workspace) and candidate != original
    assert snapshot(candidate)["digest"] == built["candidate_ref"]["candidate_digest"]
    completed = run("candidate")
    assert completed["state"] == "VERIFIED", completed
    assert snapshot(original)["digest"] == job["assessment"]["source_digest"]

    def forbidden(*unused, **kwargs):
        raise AssertionError("Stored comparison/report must not run programs or models")

    real_run, real_popen = subprocess.run, subprocess.Popen
    subprocess.run, subprocess.Popen = forbidden, forbidden
    try:
        comparison = engine.invoke("compare", {"job": jid})
        report = engine.invoke("report", {"job": jid})
        assert comparison["compared_cases"] == len(cases), comparison
        assert comparison["evidence_grade"] == "independently-observed-json-process-response", comparison
        assert comparison["candidate_passed"] == len(cases) and comparison["baseline_passed"] == len(cases)
        assert comparison["unobserved_effects"] == ["filesystem", "database", "network", "unexposed internal state"]
        assert json.loads(report["json"]) == comparison
    finally:
        subprocess.run, subprocess.Popen = real_run, real_popen
    cleanup = []
    for record in (workspace / "executions").glob("*/cleanup.json"):
        value = json.loads(record.read_text())
        cid = value["container_id"]
        removed = subprocess.run(["docker", "container", "inspect", cid], capture_output=True, text=True, timeout=15)
        assert value["removed"] and removed.returncode != 0 and "No such" in removed.stderr
        cleanup.append(cid)
    assert len(cleanup) == 2
    result = {"schema_version": 1, "status": "CONFIGURED_ENGINE_FIXTURE_JOURNEY_PASSED", "fixture_authority_only": True, "real_owner_approval_used": False, "native_host_workflow_proven": False, "engine_core_digest": snapshot(Path(__file__).resolve().parents[1] / "src/hermes_modernisation")["digest"], "job_id": jid, "final_state": completed["state"], "comparison": comparison, "container_cleanup_readback": cleanup, "source_unchanged": True, "compare_report_process_launches": 0, "limits": ["finite owned JSON process responses only", "no real owner-approved project trial", "not independent final review/release qualification"]}
    Executor._write(root / "result.json", result)
    Executor._write_bytes(root / "report.html", report["html"].encode())
    print(json.dumps({"status": result["status"], "result": str(root / "result.json")}))


if __name__ == "__main__":
    main()

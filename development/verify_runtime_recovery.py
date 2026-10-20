"""Real process-loss and cooperative-cancel proof on OWNED rootless fixtures.

Uses ephemeral fixture authority only, never Sahil's key or a real repository.
Kills owned controller children at exact durable boundaries, then requires a
separately signed public recovery. No partial output is adopted as a new run.
Every namespace and failed artifact stays retained for diagnosis.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hermes_modernisation.approvals import canonical
from hermes_modernisation.errors import ExecutionInterrupted
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError, dumps, loads
from hermes_modernisation.service import Engine
from verify_protected_capture import APP


def sign(key, field, value):
    body = {"schema_version": 1, field: value, "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 1200, "max_uses": 1}
    return {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}


def fixture(root, label, image, *, slow=False):
    root = root / label
    root.mkdir(mode=0o700)
    source = root / "source"
    source.mkdir(mode=0o755)
    raw = APP.replace("VALUE_EXPRESSION", "value * 2")
    if slow:
        raw = raw.replace("request = json.load", "import time\ntime.sleep(20)\nrequest = json.load")
    raw = raw.encode()
    (source / "app.py").write_bytes(raw)
    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    key = Ed25519PrivateKey.generate()
    config = root / "operator.json"
    Executor._write(config, {"schema_version": 1, "profile": "fixture", "workspace": str(workspace), "public_keys": {"fixture_owner": base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()}, "images": [image]})
    engine = Engine(root / "state", profile="fixture", operator_config=config)
    job = engine.invoke("assess", {"repo": str(source), "goal": "Owned runtime recovery fixture", "request_id": label})
    cases = [{"id": "fresh_" + str(i), "kind": "fresh", "input": {"value": i}, "expected": {"value": i * 2}, "rule_ids": ["double"]} for i in range(10)]
    cases += [{"id": "negative", "kind": "boundary", "input": {"value": -7}, "expected": {"value": -14}, "rule_ids": ["double"]}, {"id": "malformed", "kind": "malformed", "input": {"value": "bad"}, "expected": {"error": "invalid"}, "rule_ids": ["double"]}]
    contract = {"schema_version": 1, "kind": "BehaviourContract", "scope": "owned_recovery_json_responses", "track": "uplift", "source_digest": job["assessment"]["source_digest"], "adapter": "json-batch-v1", "runtimes": {phase: {"image": image, "argv": ["python", "-B", "/source/app.py"]} for phase in ("baseline", "candidate")}, "allowed_paths": ["app.py"], "seed": 41, "rules": [{"id": "double", "text": "Double integers and reject other types", "source_refs": [{"path": "app.py", "line_start": 3, "line_end": 7, "sha256": hashlib.sha256(raw).hexdigest()}], "case_ids": [case["id"] for case in cases]}], "cases": cases, "normalizations": [], "planned_differences": []}
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    decision = engine.invoke("review_request", {"job": job["job_id"], "purpose": "contract", "actor": "fixture_owner"})["decision"]
    engine.invoke("review", {"job": job["job_id"], "grant": sign(key, "decision", decision)})
    prepared = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "baseline", "timeout_seconds": 30, "output_limit_bytes": 65536})
    grant = sign(key, "operation", prepared["operation"])
    recover_decision = engine.invoke("control_request", {"job": job["job_id"], "attempt": prepared["attempt_id"], "purpose": "recover", "actor": "fixture_owner"})["decision"]
    recovery_grant = sign(key, "decision", recover_decision)
    Executor._write(root / "child-input.json", {"job_id": job["job_id"], "attempt_id": prepared["attempt_id"], "grant": grant, "recovery_grant": recovery_grant})
    return root, engine, job, prepared, grant, key, recovery_grant


def child(root, fault):
    data = loads((root / "child-input.json").read_bytes())
    engine = Engine(root / "state", profile="fixture", operator_config=root / "operator.json")
    if fault == "OWNERSHIP_CLAIMED":
        import hermes_modernisation.controller as controller

        def loss(*unused):
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(72)

        controller.capture = loss
    elif fault != "COOPERATIVE_CANCEL":
        original = Executor._checkpoint

        def checkpoint(self, label, details):
            original(self, label, details)
            if label == fault:
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(72)

        Executor._checkpoint = checkpoint
    try:
        engine.invoke("run", {"job": data["job_id"], "attempt": data["attempt_id"], "grant": data["grant"]})
    except ExecutionInterrupted as error:
        Executor._write(root / "interrupted.json", {"attempt_id": error.attempt_id, "execution_performed": error.execution_performed, "recovery_required": True})
        return 31
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-parent", type=Path)
    parser.add_argument("--image")
    parser.add_argument("--child", type=Path)
    parser.add_argument("--fault")
    args = parser.parse_args()
    if args.child:
        raise SystemExit(child(args.child, args.fault))
    parent = args.work_parent
    assert parent and parent.is_absolute() and parent.resolve() == parent and parent.is_dir()
    root = parent / ("recovery-" + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    rows = []
    labels = ["OWNERSHIP_CLAIMED", "AUTHORITY_CLAIMED", "START_REQUESTED", "COLLECTED", "CLEANUP_VERIFIED", "COOPERATIVE_CANCEL"]
    for label in labels:
        directory, engine, job, prepared, grant, key, recovery_grant = fixture(root, label, args.image, slow=label == "COOPERATIVE_CANCEL")
        jid, aid = job["job_id"], prepared["attempt_id"]
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(directory), "--fault", label]
        if label == "COOPERATIVE_CANCEL":
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                attempt = engine.store.attempts_for(jid)[0]
                if any(entry["label"] == "START_REQUESTED" for entry in attempt["checkpoints"]):
                    break
                assert process.poll() is None
                time.sleep(0.05)
            else:
                process.kill()
                raise AssertionError("Owned worker did not reach its declared start checkpoint")
            try:
                engine.invoke("recover", {"job": jid, "attempt": aid, "grant": recovery_grant})
            except ContractError as error:
                assert "owns" in str(error), str(error)
            else:
                raise AssertionError("Recovery stole a live worker's runtime lock")
            cancel_decision = engine.invoke("control_request", {"job": jid, "attempt": aid, "purpose": "cancel", "actor": "fixture_owner"})["decision"]
            cancelled = engine.invoke("cancel", {"job": jid, "attempt": aid, "grant": sign(key, "decision", cancel_decision)})
            assert cancelled["cancel_requested"]
            output, _ = process.communicate(timeout=20)
            status = process.returncode
            assert status == 31, output.decode()
            assert engine.store.attempts_for(jid)[0]["state"] == "CANCELLED"
        else:
            process = subprocess.run(command, capture_output=True, timeout=45)
            output, status = process.stdout + process.stderr, process.returncode
            assert status == 72, output.decode()
        Executor._write_bytes(directory / "child-output.log", output)
        prior = engine.store.attempts_for(jid)[0]
        assert not engine.store.get(jid)["execution_receipts"]
        try:
            engine.invoke("resume", {"job": jid, "attempt": aid})
        except ContractError as error:
            assert "recovery" in str(error)
        else:
            raise AssertionError("An unaccepted crashed/cancelled process resumed as evidence")
        result = engine.invoke("recover", {"job": jid, "attempt": aid, "grant": recovery_grant})
        assert result["retired"] and result["runtime_retirement"]["removed_readback"]
        assert result["state"] == "BASELINE_AUTHORITY_REQUIRED"
        assert not engine.store.get(jid)["execution_receipts"]
        assert engine.store.attempts_for(jid)[0]["state"] == "RETIRED"
        try:
            engine.invoke("run", {"job": jid, "attempt": aid, "grant": grant})
        except (ContractError, PermissionError):
            pass
        else:
            raise AssertionError("Old retired attempt/permission replayed")
        with sqlite3.connect((directory / "workspace/control/claims.sqlite").as_uri() + "?mode=ro", uri=True) as connection:
            run_claimed = connection.execute("SELECT COUNT(*) FROM claims WHERE nonce=?", (grant["body"]["nonce"],)).fetchone()[0]
        assert run_claimed == (0 if label == "OWNERSHIP_CLAIMED" else 1)
        inspected = subprocess.run(["docker", "container", "inspect", result["runtime_retirement"]["container_name"]], capture_output=True, text=True, timeout=15)
        assert inspected.returncode != 0 and "No such" in inspected.stderr
        assert snapshot(job["repo"])["digest"] == job["assessment"]["source_digest"]
        rows.append({"fault": label, "child_exit": status, "attempt_id": aid, "prior_state": prior["state"], "prior_checkpoints": [entry["label"] for entry in prior["checkpoints"]], "operation_authority_claimed": bool(run_claimed), "retired": True, "runtime_removed_readback": True, "partial_evidence_adopted": False, "old_run_refused": True, "source_unchanged": True})
    result = {"schema_version": 1, "status": "FIXTURE_CRASH_AND_CANCELLATION_RECOVERY_PASSED", "fixture_authority_only": True, "real_owner_approval_used": False, "engine_core_digest": snapshot(Path(__file__).resolve().parents[1] / "src/hermes_modernisation")["digest"], "cases": rows, "native_host_execution_proven": False, "outer_verdict": "NOT_PROVEN", "limits": ["owned Linux rootless process fixture only", "not full build-reservation or every state-machine crash acceptance", "not real owner/project execution or final independent review"]}
    Executor._write(root / "result.json", result)
    print(json.dumps({"status": result["status"], "result": str(root / "result.json"), "cases": len(rows)}))


if __name__ == "__main__":
    main()

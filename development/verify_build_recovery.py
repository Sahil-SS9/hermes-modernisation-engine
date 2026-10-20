"""Actual build-reservation crash recovery on owned rootless fixture jobs only.

A real protected baseline precedes every reviewed build. Controller children
are terminated before, during or after copy. Explicit signed recovery must
quarantine the reserved path, require a fresh review, and rebuild elsewhere.
No real owner/project, model call, installation or deletion is involved.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError, loads
from hermes_modernisation.service import Engine
from verify_runtime_recovery import fixture, sign


def child(root, fault):
    import hermes_modernisation.candidates as candidates
    import hermes_modernisation.proposals as proposals

    data = loads((root / "child-input.json").read_bytes())
    original = candidates.stage_candidate

    def stage(source, destination, proposal):
        if fault == "BEFORE_COPY":
            os._exit(73)
        if fault == "DURING_COPY":
            read = proposals.read_source

            def interrupted_read(*args):
                if Path(destination).exists():
                    os._exit(73)
                return read(*args)

            proposals.read_source = interrupted_read
        result = original(source, destination, proposal)
        if fault == "AFTER_COPY":
            os._exit(73)
        return result

    candidates.stage_candidate = stage
    engine = Engine(root / "state", profile="fixture", operator_config=root / "operator.json")
    engine.invoke("build", {"job": data["job_id"]})
    return 0


def main():
    import uuid

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
    root = parent / ("build-recovery-" + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    rows = []
    for label in ("BEFORE_COPY", "DURING_COPY", "AFTER_COPY"):
        directory, engine, job, prepared, grant, key, _ = fixture(root, label, args.image)
        jid = job["job_id"]
        baseline = engine.invoke("run", {"job": jid, "attempt": prepared["attempt_id"], "grant": grant})
        assert baseline["state"] == "BASELINED" and baseline["baseline_ref"]["passed"] == 12
        raw = (Path(job["repo"]) / "app.py").read_bytes()
        proposal = {"schema_version": 1, "source_digest": job["assessment"]["source_digest"], "goal": job["goal"], "changes": [{"path": "app.py", "before_sha256": hashlib.sha256(raw).hexdigest(), "replacement": raw.decode().replace("value * 2", "value + value")}], "allowed_paths": ["app.py"], "planned_differences": []}
        engine.invoke("proposal", {"job": jid, "revision": baseline["revision"], "proposal": proposal})
        review = engine.invoke("review_request", {"job": jid, "purpose": "migration", "actor": "fixture_owner"})["decision"]
        engine.invoke("review", {"job": jid, "grant": sign(key, "decision", review)})
        process = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(directory), "--fault", label], capture_output=True, timeout=30)
        Executor._write_bytes(directory / "child-output.log", process.stdout + process.stderr)
        assert process.returncode == 73, (process.stdout + process.stderr).decode()
        interrupted = engine.store.get(jid)
        reservation = interrupted["candidate_reservation"]
        old = Path(reservation["path"])
        before = snapshot(old) if old.exists() else None
        decision = engine.invoke("control_request", {"job": jid, "attempt": reservation["id"], "purpose": "recover_build", "actor": "fixture_owner"})["decision"]
        assert decision["container_name"] is None
        recovered = engine.invoke("recover_build", {"job": jid, "attempt": reservation["id"], "grant": sign(key, "decision", decision)})
        assert recovered["quarantined"] is True and recovered["fresh_review_required"] is True
        assert recovered["state"] == "PLAN_REVIEW_REQUIRED"
        assert (snapshot(old) if old.exists() else None) == before
        try:
            engine.invoke("build", {"job": jid})
        except ContractError:
            pass
        else:
            raise AssertionError("Recovered build reused an old migration review")
        review = engine.invoke("review_request", {"job": jid, "purpose": "migration", "actor": "fixture_owner"})["decision"]
        engine.invoke("review", {"job": jid, "grant": sign(key, "decision", review)})
        built = engine.invoke("build", {"job": jid})
        new = Path(built["candidate_ref"]["path"])
        assert new != old and new.is_dir() and built["state"] == "CANDIDATE_BUILT"
        assert (snapshot(old) if old.exists() else None) == before
        assert snapshot(job["repo"])["digest"] == job["assessment"]["source_digest"]
        rows.append({"fault": label, "child_exit": 73, "job_id": jid, "quarantined_candidate_id": reservation["id"], "fresh_candidate_id": built["candidate_ref"]["id"], "failed_path_preserved": True, "fresh_review_required_and_exercised": True, "new_namespace": True, "source_unchanged": True, "baseline_passed": 12, "candidate_executed": False})
    result = {"schema_version": 1, "status": "FIXTURE_BUILD_RESERVATION_RECOVERY_PASSED", "fixture_authority_only": True, "real_owner_approval_used": False, "engine_core_digest": snapshot(Path(__file__).resolve().parents[1] / "src/hermes_modernisation")["digest"], "cases": rows, "limits": ["owned three-boundary build fixture only", "not full state/platform/native/release qualification", "baseline actually executed; rebuilt candidate not executed by this probe"]}
    Executor._write(root / "result.json", result)
    print(json.dumps({"status": result["status"], "result": str(root / "result.json"), "cases": len(rows)}))


if __name__ == "__main__":
    main()

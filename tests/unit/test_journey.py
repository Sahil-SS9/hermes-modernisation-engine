"""One owned-fixture journey through the native assess-to-report interfaces.

The runtime collector is a declared offline fixture: it writes the exact
private artifacts the trusted collector would write and returns the same
ProtectedCapture shape.  Every state transition, grant, journal checkpoint,
observation acceptance, candidate materialisation, comparison and report is the
real public engine path.  No Docker process or model is launched.
"""

import base64
import hashlib
import time
import uuid

import pytest

from hermes_modernisation.approvals import canonical
from hermes_modernisation.baseline import evaluate_response, make_inputs, wire_id
from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.service import Engine
from test_review_requests import configured_fixture, signed_review


def operation_grant(key, operation, field="operation"):
    body = {
        "schema_version": 1,
        field: operation,
        "nonce": "fixture_" + uuid.uuid4().hex,
        "expires_at": time.time() + 300,
        "max_uses": 1,
    }
    return {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}


def fixture_capture(key):
    def capture(executor, grant, operation, source, oracle, contract):
        attempt_id = operation["attempt_id"]
        phase = executor.phase
        executor.authority.claim(grant, operation)
        executor._checkpoint_callback("AUTHORITY_CLAIMED", {"phase": phase})
        executor._checkpoint_callback("START_REQUESTED", {"phase": phase})
        payload = make_inputs(contract, attempt_id)
        raw = dumps(
            {
                "schema_version": 1,
                "results": [
                    {
                        "id": wire_id(attempt_id, case["id"]),
                        "output": case["expected"],
                    }
                    for case in contract["cases"]
                ],
            }
        )
        folder = executor.root / attempt_id
        folder.mkdir(parents=True, mode=0o700)
        receipt = {
            "schema_version": 1,
            "kind": "ExecutionReceipt",
            "grade": "observed-process-only",
            "actor": operation["actor"],
            "profile": operation["profile"],
            "job_id": operation["job_id"],
            "attempt_id": attempt_id,
            "phase": phase,
            "source_digest": operation["source_digest"],
            "oracle_digest": operation["oracle_digest"],
            "environment_digest": operation["environment_digest"],
            "image": executor.image,
            "authority_nonce": grant["body"]["nonce"],
            "process_exit_code": 0,
            "timed_out": False,
            "truncated": False,
            "output_bytes": len(raw),
            "input_sha256": hashlib.sha256(payload).hexdigest(),
            "input_bytes": len(payload),
            "input_complete": True,
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "duration_seconds": 0.25,
            "container_removed": True,
            "source_unchanged": True,
            "verdict": "NOT_PROVEN",
            "missing_evidence": ["fixture collector, not a process launch"],
        }
        for name, value in (
            ("receipt.json", dumps(receipt)),
            ("cleanup.json", dumps({"removed": True})),
            ("output.bin", raw),
        ):
            path = folder / name
            path.write_bytes(value)
            path.chmod(0o600)
        executor._checkpoint_callback("COLLECTED", {"phase": phase})
        executor._checkpoint_callback("CLEANUP_VERIFIED", {"phase": phase})
        return {
            "schema_version": 1,
            "kind": "ProtectedCapture",
            "phase": phase,
            "job_id": operation["job_id"],
            "attempt_id": attempt_id,
            "operation": operation,
            "receipt": receipt,
            "evaluation": evaluate_response(contract, attempt_id, raw),
            "capture_origin": "trusted-executor-direct-return-and-private-readback",
            "raw_output_sha256": receipt["output_sha256"],
            "artifact_root": str(folder),
            "verdict": "NOT_PROVEN",
            "execution_performed": True,
        }

    return capture


def run_attempt(engine, job, key, monkeypatch):
    attempt = engine.invoke(
        "prepare",
        {
            "job": job["job_id"],
            "phase": "baseline" if not job.get("baseline_ref") else "candidate",
            "actor": "fixture_owner",
            "request_id": "journey_" + uuid.uuid4().hex,
            "timeout_seconds": 20,
            "output_limit_bytes": 65536,
        },
    )
    grant = operation_grant(key, attempt["operation"])
    return engine.invoke(
        "run", {"job": job["job_id"], "attempt": attempt["attempt_id"], "grant": grant}
    )


def test_complete_owned_fixture_journey_and_zero_launch_compare(tmp_path, monkeypatch):
    engine, job, contract, key, workspace, config = configured_fixture(tmp_path)
    monkeypatch.setattr("hermes_modernisation.controller.capture", fixture_capture(key))
    engine.invoke("review", {"job": job["job_id"], "grant": signed_review(engine, job, key)})
    job = engine.invoke("status", {"job": job["job_id"]})
    plan = engine.invoke("plan", {"job": job["job_id"], "revision": job["revision"]})
    assert plan["state"] in {"BASELINE_AUTHORITY_REQUIRED", "PLAN_REVIEW_REQUIRED"}
    job = run_attempt(engine, job, key, monkeypatch)
    assert job["state"] == "BASELINED" and job["execution_receipts"]

    restored = Engine(engine.store.root, operator_config=config)
    assert restored.invoke("status", {"job": job["job_id"]})["state"] == "BASELINED"
    baseline_attempt = next(
        row
        for row in engine.invoke("attempts", {"job": job["job_id"]})["attempts"]
        if row["state"] == "COMPLETED"
    )
    resumed = engine.invoke(
        "resume", {"job": job["job_id"], "attempt": baseline_attempt["attempt_id"]}
    )
    assert resumed["state"] == "BASELINED"

    job = engine.invoke("status", {"job": job["job_id"]})
    from hermes_modernisation.batches import FixtureProposer

    replacement = "def calculate(value):\n    return value + value\n"
    engine.proposer = FixtureProposer(
        {
            "single": {
                "text": dumps(
                    {
                        "schema_version": 1,
                        "batch_id": "single",
                        "changes": [{"path": "app.py", "replacement": replacement}],
                    }
                ).decode(),
                "usage": {"input_tokens": 20, "output_tokens": 20},
            }
        }
    )
    applied = engine.invoke(
        "propose_batches",
        {
            "job": job["job_id"],
            "batches": [
                {"batch_id": "single", "paths": ["app.py"], "instruction": "modernise the function"}
            ],
            "budget": {
                "max_calls": 1,
                "max_input_bytes": 100000,
                "max_output_bytes": 100000,
                "max_seconds": 30,
                "max_tokens": 1000,
            },
        },
    )
    job = applied["job"]
    assert applied["model_calls"] == 1 and applied["live_model_call"] is False
    assert job["state"] == "PLAN_REVIEW_REQUIRED" and job["proposal_ref"]
    migration = engine.invoke(
        "review_request",
        {"job": job["job_id"], "purpose": "migration", "actor": "fixture_owner"},
    )["decision"]
    migration_grant = {
        "body": {
            "schema_version": 1,
            "decision": migration,
            "nonce": "fixture_" + uuid.uuid4().hex,
            "expires_at": time.time() + 300,
            "max_uses": 1,
        }
    }
    migration_grant["signature"] = base64.b64encode(
        key.sign(canonical(migration_grant["body"]))
    ).decode()
    engine.invoke("review", {"job": job["job_id"], "grant": migration_grant})
    job = engine.invoke("build", {"job": job["job_id"]})
    assert job["state"] == "CANDIDATE_BUILT" and job["candidate_ref"]
    job = run_attempt(engine, job, key, monkeypatch)
    assert job["state"] == "VERIFIED"

    def forbidden(*args, **kwargs):
        raise AssertionError("compare/report must not launch a process or model")

    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    assert comparison["verdict"] == "NOT_PROVEN"
    assert comparison["execution_performed"] is False
    assert comparison["compared_cases"] == len(contract["cases"])
    report = engine.invoke("report", {"job": job["job_id"]})
    assert report["proof_report"]["verdict"] == "NOT_PROVEN"
    assert report["proof_report"]["execution_performed"] is False
    assert "NOT_PROVEN" in report["html"]


def test_cancelled_and_uncertain_attempts_refuse_replay(tmp_path):
    engine, job, contract, key, workspace, config = configured_fixture(tmp_path)
    engine.invoke("review", {"job": job["job_id"], "grant": signed_review(engine, job, key)})
    attempt = engine.invoke(
        "prepare",
        {
            "job": job["job_id"],
            "phase": "baseline",
            "actor": "fixture_owner",
            "request_id": "cancel_journey",
            "timeout_seconds": 20,
            "output_limit_bytes": 65536,
        },
    )
    decision = engine.invoke(
        "control_request",
        {
            "job": job["job_id"],
            "attempt": attempt["attempt_id"],
            "actor": "fixture_owner",
            "purpose": "cancel",
        },
    )["decision"]
    cancelled = engine.invoke(
        "cancel",
        {"job": job["job_id"], "attempt": attempt["attempt_id"], "grant": operation_grant(key, decision, "decision")},
    )
    assert cancelled["cancel_requested"] is True
    with pytest.raises(ContractError, match="recovery|uncertain|replay"):
        engine.invoke(
            "resume", {"job": job["job_id"], "attempt": attempt["attempt_id"]}
        )
    engine.store.claim_attempt(
        job["job_id"], attempt["attempt_id"], "lost_worker", now=100, lease_seconds=1
    )
    with pytest.raises(ContractError, match="recovery|uncertain|replay|ownership"):
        engine.invoke(
            "resume", {"job": job["job_id"], "attempt": attempt["attempt_id"]}
        )

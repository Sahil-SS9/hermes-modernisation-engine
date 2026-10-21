"""Trusted collection acceptance and read-only re-verification, never an import API."""

import hashlib
from pathlib import Path

from .baseline import evaluate_response, make_inputs, read_artifact
from .contracts import fields
from .evidence_contracts import OBSERVED_GRADE, validate_receipt
from .identity import snapshot
from .jsonio import ContractError, dumps, loads, MAX_BYTES
from .runtime import environment_spec
from .state import _attempt, _job, _owned, _save, timestamp

GRADE = OBSERVED_GRADE
CHECKPOINTS = ["AUTHORITY_CLAIMED", "START_REQUESTED", "COLLECTED", "CLEANUP_VERIFIED"]


def complete(store, job_id, attempt_id, lease, captured, grant):
    """Called solely with a direct configured collector result by the controller."""
    if captured["job_id"] != job_id or captured["attempt_id"] != attempt_id:
        raise ContractError("Capture identity differs from claimed attempt")
    value = {"schema_version": 1, "kind": "ObservedExecution", "capture": captured, "grant": grant}
    raw = dumps(value)
    sha = hashlib.sha256(raw).hexdigest()
    evaluation = captured["evaluation"]
    reference = {"schema_version": 1, "kind": "ObservationReference", "attempt_id": attempt_id, "sha256": sha, "phase": captured["phase"], "oracle_digest": captured["operation"]["oracle_digest"], "source_digest": captured["operation"]["source_digest"], "passed": evaluation["passed"], "failed": evaluation["failed"], "grade": GRADE}
    with store.connection() as connection:
        job = _job(connection, job_id)
        attempt = _attempt(connection, job_id, attempt_id)
        _owned(job, attempt, lease, timestamp())
        if [entry["label"] for entry in attempt["checkpoints"]] != CHECKPOINTS or dumps(attempt["operation"]) != dumps(captured["operation"]) or captured["phase"] != attempt["phase"]:
            raise ContractError("Collected result does not match the fenced complete execution journal")
        connection.execute("INSERT INTO observations VALUES (?,?,?,?,?)", (attempt_id, job_id, attempt["phase"], raw, sha))
        attempt.update(state="COMPLETED", _lease=None, execution_performed=True)
        job["fence_epoch"] += 1
        if attempt["phase"] == "baseline":
            job.update(baseline_ref=reference, state="BASELINED" if evaluation["failed"] == 0 else "FAILED")
        else:
            job.update(candidate_observation_ref=reference, state="VERIFIED" if evaluation["failed"] == 0 else "FAILED")
        job["execution_receipts"].append(reference)
        _save(connection, job, attempt)
    return job


def read_one(store, job, reference, policy):
    """Re-derive a saved observation from its private artifacts and exact claim."""
    from .candidates import candidate_for
    from .reviews import accepted

    fields(reference, {"schema_version", "kind", "attempt_id", "sha256", "phase", "oracle_digest", "source_digest", "passed", "failed", "grade"}, "observation reference")
    aid = reference["attempt_id"]
    with store.read_connection() as connection:
        row = connection.execute("SELECT phase,body,body_sha256 FROM observations WHERE attempt_id=? AND job_id=?", (aid, job["job_id"])).fetchone()
        attempt = _attempt(connection, job["job_id"], aid)
    if row is None or row[0] != reference["phase"] or hashlib.sha256(row[1]).hexdigest() != row[2] or row[2] != reference["sha256"]:
        raise ContractError("Stored observation missing or corrupted")
    value = loads(row[1])
    fields(value, {"schema_version", "kind", "capture", "grant"}, "observed execution")
    if value["schema_version"] != 1 or type(value["schema_version"]) is not int or value["kind"] != "ObservedExecution":
        raise ContractError("Stored observation schema corrupted")
    captured = value["capture"]
    fields(captured, {"schema_version", "kind", "phase", "job_id", "attempt_id", "operation", "receipt", "evaluation", "capture_origin", "raw_output_sha256", "artifact_root", "verdict", "execution_performed"}, "protected capture")
    operation = captured["operation"]
    phase = captured["phase"]
    if phase != reference["phase"] or captured["job_id"] != job["job_id"] or captured["attempt_id"] != aid or operation != attempt["operation"] or attempt["state"] != "COMPLETED" or [entry["label"] for entry in attempt["checkpoints"]] != CHECKPOINTS:
        raise ContractError("Stored observation has contradictory job/attempt/phase bindings")
    if reference["grade"] != GRADE or captured["capture_origin"] != "trusted-executor-direct-return-and-private-readback" or captured["execution_performed"] is not True:
        raise ContractError("Stored observation origin is not an accepted collector result")
    accepted(store, job, "contract", policy)
    if phase == "baseline":
        expected_source = job["assessment"]["source_digest"]
    else:
        accepted(store, job, "migration", policy)
        expected_source = candidate_for(store, job, policy)["candidate_digest"]
    contract = store.contract_for(job["job_id"])
    runtime = contract["runtimes"][phase]
    payload = make_inputs(contract, aid)
    environment = environment_spec(operation, runtime["image"], phase, hashlib.sha256(payload).hexdigest())
    if operation["source_digest"] != expected_source or operation["candidate_digest"] != expected_source or reference["source_digest"] != expected_source or operation["profile"] != policy.profile or operation["oracle_digest"] != job["behaviour_contract"]["digest"] or reference["oracle_digest"] != operation["oracle_digest"] or operation["environment_digest"] != hashlib.sha256(dumps(environment)).hexdigest() or operation["argv"] != runtime["argv"] or operation["image_digest"] != runtime["image"].split("@sha256:")[-1]:
        raise ContractError("Observed source/contract/runtime/environment is stale or contradictory")
    policy.authority().verify_recorded(value["grant"], operation)
    folder = policy.workspace / "executions" / aid
    if captured["artifact_root"] != str(folder) or folder.resolve() != folder:
        raise ContractError("Observed capture artifact location differs from trusted workspace")
    receipt = loads(read_artifact(folder / "receipt.json", MAX_BYTES))
    cleanup = loads(read_artifact(folder / "cleanup.json", MAX_BYTES))
    raw = read_artifact(folder / "output.bin", operation["output_limit_bytes"])
    if receipt != captured["receipt"] or cleanup.get("removed") is not True:
        raise ContractError("Observed process collection/cleanup changed or is incomplete")
    bindings = {
        "job_id": job["job_id"], "attempt_id": aid, "profile": operation["profile"],
        "phase": phase, "source_digest": operation["source_digest"],
        "oracle_digest": operation["oracle_digest"],
        "environment_digest": operation["environment_digest"],
        "image": runtime["image"], "authority_nonce": value["grant"]["body"]["nonce"],
        "input_bytes": len(payload), "input_sha256": hashlib.sha256(payload).hexdigest(),
    }
    validate_receipt(receipt, bindings=bindings, require_collected=True)
    if len(raw) != receipt["output_bytes"] or hashlib.sha256(raw).hexdigest() != receipt["output_sha256"] or captured["raw_output_sha256"] != receipt["output_sha256"]:
        raise ContractError("Observed process output artifact changed")
    evaluation = evaluate_response(contract, aid, raw)
    if dumps(evaluation) != dumps(captured["evaluation"]) or reference["passed"] != evaluation["passed"] or reference["failed"] != evaluation["failed"]:
        raise ContractError("Stored observed evaluation/counts differ from protected recomputation")
    return evaluation


def comparison(store, job, policy):
    if snapshot(Path(job["repo"]))["digest"] != job["assessment"]["source_digest"]:
        raise ContractError("Assessed source changed; observed evidence is stale")
    baseline = job.get("baseline_ref")
    candidate = job.get("candidate_observation_ref")
    result = {"schema_version": 1, "job_id": job["job_id"], "scope": job["goal"], "contract_scope": store.contract_for(job["job_id"])["scope"], "source_digest": job["assessment"]["source_digest"], "verdict": "NOT_PROVEN", "evidence_grade": GRADE, "execution_performed": False, "compared_cases": 0, "approved_differences": [], "missing_evidence": ["Reviewed rule adequacy and behavioural mutation controls are not yet accepted"], "unobserved_effects": ["filesystem", "database", "network", "unexposed internal state"]}
    old = read_one(store, job, baseline, policy) if baseline else None
    new = read_one(store, job, candidate, policy) if candidate else None
    if old is None or new is None:
        result["missing_evidence"].append("Protected baseline/candidate observation pair is incomplete")
        return result
    if len(old["cases"]) != len(new["cases"]) or any((a["id"], a["input_digest"]) != (b["id"], b["input_digest"]) for a, b in zip(old["cases"], new["cases"], strict=True)):
        raise ContractError("Observed phases do not cover the same protected input identities")
    rows = [{"id": a["id"], "input_digest": a["input_digest"], "baseline_matches_expected": a["matches_expected"], "candidate_matches_expected": b["matches_expected"], "same_output": dumps({"value": a["output"]}) == dumps({"value": b["output"]}), "rule_ids": a["rule_ids"]} for a, b in zip(old["cases"], new["cases"], strict=True)]
    result.update(compared_cases=len(rows), baseline_passed=old["passed"], candidate_passed=new["passed"], baseline_failed=old["failed"], candidate_failed=new["failed"], cases=rows, baseline_receipt=baseline, candidate_receipt=candidate)
    if old["failed"] or new["failed"]:
        result["missing_evidence"].append("Observed responses fail the unchanged protected oracle")
    return result

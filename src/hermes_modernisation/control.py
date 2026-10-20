"""Exact signed cooperative cancellation and explicit no-replay runtime retirement."""

import hashlib
import json
import subprocess
import uuid

from .contracts import digest, fields
from .identity import snapshot
from .jsonio import ContractError, dumps, identifier
from .state import _attempt, _job, _save

DECISION_FIELDS = {"schema_version", "kind", "job_id", "attempt_id", "profile", "actor", "purpose", "operation_digest", "container_name"}


def validate_decision(value):
    fields(value, DECISION_FIELDS, "control decision")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "ControlDecision" or value["purpose"] not in ("cancel", "recover"):
        raise ContractError("Unsupported owner control decision")
    for key in ("job_id", "attempt_id", "profile", "actor"):
        identifier(value[key])
    digest(value["operation_digest"])
    expected = "modernise-" + hashlib.sha256(value["attempt_id"].encode()).hexdigest()[:32]
    if value["container_name"] != expected:
        raise ContractError("Control container identity differs from exact stored attempt")
    return value


def request(store, job, attempt_id, purpose, actor, profile):
    identifier(actor)
    with store.read_connection() as connection:
        attempt = _attempt(connection, job["job_id"], attempt_id)
    return {"decision": validate_decision({"schema_version": 1, "kind": "ControlDecision", "job_id": job["job_id"], "attempt_id": attempt_id, "profile": profile, "actor": actor, "purpose": purpose, "operation_digest": hashlib.sha256(dumps(attempt["operation"])).hexdigest(), "container_name": "modernise-" + hashlib.sha256(attempt_id.encode()).hexdigest()[:32]}), "permission_granted": False, "execution_performed": False}


def verified(store, job, attempt_id, purpose, grant, policy):
    if type(grant) is not dict or type(grant.get("body")) is not dict or type(grant["body"].get("decision")) is not dict:
        raise ContractError("A signed exact owner control grant is required")
    decision = validate_decision(grant["body"]["decision"])
    expected = request(store, job, attempt_id, purpose, decision["actor"], policy.profile)["decision"]
    if dumps(decision) != dumps(expected):
        raise ContractError("Owner control decision differs from this job/attempt/profile")
    policy.authority().verify_control(grant, decision)
    return decision


def cancelled(store, job_id, attempt_id):
    reference = store.get(job_id).get("cancel_ref")
    return type(reference) is dict and reference.get("attempt_id") == attempt_id


def cancel(store, job, attempt_id, grant, policy):
    decision = verified(store, job, attempt_id, "cancel", grant, policy)
    with store.read_connection() as connection:
        attempt = _attempt(connection, job["job_id"], attempt_id)
    if attempt["state"] in {"COMPLETED", "RETIRED"}:
        raise ContractError("Completed/retired work cannot be cancelled or re-executed")
    nonce = policy.authority(create=True).claim_control(grant, decision)
    reference = {"id": uuid.uuid4().hex, "attempt_id": attempt_id, "purpose": "cancel", "authority_nonce": nonce, "authenticated": True}
    raw = dumps({"reference": reference, "grant": grant})
    with store.connection() as connection:
        current = _job(connection, job["job_id"])
        attempt = _attempt(connection, job["job_id"], attempt_id)
        if attempt["state"] in {"COMPLETED", "RETIRED"}:
            raise ContractError("Worker completed before cancellation; control grant consumed, no replay")
        connection.execute("INSERT INTO reviews VALUES (?,?,?,?,?)", (reference["id"], job["job_id"], "cancel", raw, hashlib.sha256(raw).hexdigest()))
        current["cancel_ref"] = reference
        current["revision"] += 1
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(current), job["job_id"]))
    return {"schema_version": 1, "job_id": job["job_id"], "attempt_id": attempt_id, "cancel_requested": True, "execution_performed": False, "runtime_retirement_confirmed": False, "message": "Cooperative owner stop requested; the worker retains runtime ownership until cleanup. Lost workers need separately signed recovery."}


def recover(store, job, attempt_id, grant, policy):
    from .runtime_lock import locked

    decision = verified(store, job, attempt_id, "recover", grant, policy)
    with locked(policy, job["job_id"]):
        job = store.get(job["job_id"])
        with store.read_connection() as connection:
            attempt = _attempt(connection, job["job_id"], attempt_id)
            other = connection.execute("SELECT id FROM attempts WHERE job_id=? AND id<>? AND state IN ('RUNNING','CLAIMED','COLLECTED')", (job["job_id"], attempt_id)).fetchone()
        if other is not None:
            raise ContractError("A different attempt owns this job; recovery cannot revoke another worker")
        if (attempt["phase"] == "baseline" and job.get("baseline_ref")) or (attempt["phase"] == "candidate" and job.get("candidate_observation_ref")):
            raise ContractError("This phase already has an accepted observation; obsolete attempt recovery cannot reset later workflow state")
        if attempt["state"] in {"COMPLETED", "RETIRED"}:
            raise ContractError("Completed/retired attempt cannot be recovered or replayed")
        security = subprocess.run(["docker", "info", "--format", "{{json .SecurityOptions}}"], capture_output=True, text=True, timeout=15)
        if security.returncode or "name=rootless" not in json.loads(security.stdout):
            raise ContractError("Rootless runtime recovery unavailable; no state/authority reset")
        authority = policy.authority(create=True)
        nonce = authority.claim_control(grant, decision)
        # Revoke every old fencing token BEFORE any external runtime retirement.
        with store.connection() as connection:
            current = _job(connection, job["job_id"])
            attempt = _attempt(connection, job["job_id"], attempt_id)
            current.update(state="RECOVERY_REQUIRED", fence_epoch=current.get("fence_epoch", 0) + 1)
            attempt.update(state="INTERRUPTED", _lease=None, failure_reason="Owner-authorised runtime retirement pending; no replay")
            _save(connection, current, attempt)
        name = decision["container_name"]
        inspected = subprocess.run(["docker", "container", "inspect", name], capture_output=True, text=True, timeout=15)
        container_id = None
        if inspected.returncode == 0:
            actual = json.loads(inspected.stdout)
            if type(actual) is not list or len(actual) != 1:
                raise ContractError("Ambiguous runtime identity; recovery remains required")
            actual = actual[0]
            runtime_image = next((image for image in policy.images if image.endswith("@sha256:" + attempt["operation"]["image_digest"])), None)
            if runtime_image is None or actual.get("Name") != "/" + name or actual.get("Config", {}).get("Image") != runtime_image or actual.get("HostConfig", {}).get("NetworkMode") != "none" or actual.get("HostConfig", {}).get("ReadonlyRootfs") is not True:
                raise ContractError("Runtime identity/policy differs; refuse to retire an unrelated container")
            container_id = digest(actual.get("Id"))
            removed = subprocess.run(["docker", "rm", "-f", container_id], capture_output=True, text=True, timeout=15)
            if removed.returncode:
                raise ContractError("Runtime retirement failed; recovery remains required")
        elif "No such" not in inspected.stderr:
            raise ContractError("Runtime identity unavailable; recovery remains required")
        absent = subprocess.run(["docker", "container", "inspect", name], capture_output=True, text=True, timeout=15)
        if absent.returncode == 0 or "No such" not in absent.stderr:
            raise ContractError("Runtime retirement readback failed; recovery remains required")
        reference = {"schema_version": 1, "kind": "RuntimeRetirement", "id": uuid.uuid4().hex, "job_id": job["job_id"], "attempt_id": attempt_id, "container_name": name, "container_id": container_id, "authority_nonce": nonce, "removed_readback": True, "execution_replayed": False, "adopted_partial_evidence": False}
        raw = dumps({"reference": reference, "grant": grant})
        source_matches = snapshot(job["repo"])["digest"] == job["assessment"]["source_digest"]
        restore_state = "BASELINE_AUTHORITY_REQUIRED" if attempt["phase"] == "baseline" else "CANDIDATE_BUILT"
        if not source_matches:
            restore_state = "BLOCKED_PREREQUISITE"
        with store.connection() as connection:
            current = _job(connection, job["job_id"])
            attempt = _attempt(connection, job["job_id"], attempt_id)
            if current["state"] != "RECOVERY_REQUIRED":
                raise ContractError("Recovery state changed; residue retained, no automatic replay")
            attempt.update(state="RETIRED", _lease=None, failure_reason="Exact owner-authorised runtime retirement complete; old permission stays spent")
            current.update(state=restore_state, recovery_ref=reference)
            current.pop("cancel_ref", None)
            connection.execute("INSERT INTO reviews VALUES (?,?,?,?,?)", (reference["id"], job["job_id"], "recover", raw, hashlib.sha256(raw).hexdigest()))
            _save(connection, current, attempt)
        return {"schema_version": 1, "job_id": job["job_id"], "attempt_id": attempt_id, "retired": True, "state": restore_state, "runtime_retirement": reference, "execution_performed": False, "fresh_exact_operation_grant_required": True}

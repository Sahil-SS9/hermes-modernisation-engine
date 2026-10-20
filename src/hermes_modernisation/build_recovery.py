"""Owner-authorised quarantine of crashed build reservations; no deletion/reuse."""

import hashlib
import uuid

from .identity import snapshot
from .jsonio import ContractError, dumps, loads
from .state import _job


def request_decision(job, candidate_id, actor, profile):
    reservation = job.get("candidate_reservation")
    if type(reservation) is not dict or reservation.get("id") != candidate_id or reservation.get("job_id") != job["job_id"] or reservation.get("state") != "BUILDING":
        raise ContractError("No exact unfinished candidate reservation in this job")
    if job["state"] not in {"CANDIDATE_BUILDING", "INTERRUPTED"}:
        raise ContractError("Build reservation recovery unavailable in this workflow state")
    return {"schema_version": 1, "kind": "ControlDecision", "job_id": job["job_id"], "attempt_id": candidate_id, "profile": profile, "actor": actor, "purpose": "recover_build", "operation_digest": hashlib.sha256(dumps(reservation)).hexdigest(), "container_name": None}


def recover(store, job, candidate_id, grant, policy):
    from .control import verified
    from .runtime_lock import locked

    decision = verified(store, job, candidate_id, "recover_build", grant, policy)
    with locked(policy, job["job_id"]):
        current = store.get(job["job_id"])
        expected = request_decision(current, candidate_id, decision["actor"], policy.profile)
        if dumps(expected) != dumps(decision):
            raise ContractError("Build reservation changed during recovery request")
        reservation = current["candidate_reservation"]
        expected_path = policy.workspace / "candidates" / job["job_id"] / candidate_id
        if reservation["path"] != str(expected_path):
            raise ContractError("Candidate reservation is outside its engine-owned scope")
        with store.read_connection() as connection:
            row = connection.execute("SELECT path,body,body_sha256 FROM candidates WHERE id=? AND job_id=?", (candidate_id, job["job_id"])).fetchone()
        if row is None or row[0] != str(expected_path) or hashlib.sha256(row[1]).hexdigest() != row[2] or loads(row[1]) != reservation:
            raise ContractError("Candidate reservation storage corrupted")
        # No copy, chmod, rename, cleanup or program is run on the failed path.
        try:
            source_current = snapshot(job["repo"])["digest"] == job["assessment"]["source_digest"]
        except (ContractError, OSError):
            source_current = False
        nonce = policy.authority(create=True).claim_control(grant, decision)
        reference = {"schema_version": 1, "kind": "BuildReservationQuarantine", "id": uuid.uuid4().hex, "job_id": job["job_id"], "candidate_id": candidate_id, "path": str(expected_path), "reservation_digest": decision["operation_digest"], "authority_nonce": nonce, "failed_path_preserved": True, "fresh_review_required": True, "fresh_candidate_namespace_required": True, "execution_performed": False}
        raw = dumps({"reference": reference, "grant": grant})
        quarantined = {**reservation, "state": "QUARANTINED", "recovery_id": reference["id"]}
        candidate_raw = dumps(quarantined)
        with store.connection() as connection:
            latest = _job(connection, job["job_id"])
            if latest["revision"] != current["revision"] or latest.get("candidate_reservation") != reservation:
                raise ContractError("Build state changed; control grant consumed, no automatic replay")
            connection.execute("UPDATE candidates SET body=?,body_sha256=? WHERE id=? AND job_id=?", (candidate_raw, hashlib.sha256(candidate_raw).hexdigest(), candidate_id, job["job_id"]))
            connection.execute("INSERT INTO reviews VALUES (?,?,?,?,?)", (reference["id"], job["job_id"], "recover_build", raw, hashlib.sha256(raw).hexdigest()))
            latest.pop("candidate_reservation")
            latest.pop("migration_review", None)
            latest.update(state="PLAN_REVIEW_REQUIRED" if source_current else "BLOCKED_PREREQUISITE", build_recovery_ref=reference, fence_epoch=latest.get("fence_epoch", 0) + 1, revision=latest["revision"] + 1)
            connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(latest), job["job_id"]))
        return {"schema_version": 1, "job_id": job["job_id"], "candidate_id": candidate_id, "quarantined": True, "state": latest["state"], "fresh_review_required": True, "fresh_candidate_namespace_required": True, "failed_path_preserved": True, "execution_performed": False}

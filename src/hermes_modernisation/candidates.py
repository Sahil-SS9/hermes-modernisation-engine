"""Engine-owned proposal binding and isolated, reviewed candidate materialisation."""

import hashlib
import uuid
from pathlib import Path

from .contracts import fields
from .identity import snapshot
from .jsonio import ContractError, dumps, loads
from .proposals import stage_candidate, validate_proposal
from .state import _job


def save_proposal(store, job, revision, proposal):
    if not job.get("baseline_ref") or job["state"] not in {"BASELINED", "PLAN_REVIEW_REQUIRED"}:
        raise ContractError("An accepted protected baseline is required before a migration proposal")
    if type(revision) is not int or revision != job["revision"]:
        raise ContractError("Stale job revision")
    contract = store.contract_for(job["job_id"])
    value, _ = validate_proposal(job["repo"], proposal)
    if value["goal"] != job["goal"] or not set(value["allowed_paths"]) <= set(contract["allowed_paths"]):
        raise ContractError("Proposal differs from the declared goal or protected path scope")
    raw = dumps(value)
    digest = hashlib.sha256(raw).hexdigest()
    reference = {"schema_version": 1, "kind": "SourceProposalReference", "digest": digest, "source_digest": value["source_digest"], "paths": value["allowed_paths"]}
    with store.connection() as connection:
        current = _job(connection, job["job_id"], store.profile)
        if current["revision"] != revision or current["state"] not in {"BASELINED", "PLAN_REVIEW_REQUIRED"}:
            raise ContractError("Job changed before proposal registration")
        row = connection.execute("SELECT body FROM details WHERE hash=?", (digest,)).fetchone()
        if row is not None and row[0] != raw:
            raise ContractError("Proposal storage corrupted")
        connection.execute("INSERT OR IGNORE INTO details VALUES (?,?)", (digest, raw))
        current.update(proposal_ref=reference, state="PLAN_REVIEW_REQUIRED", revision=revision + 1)
        current.pop("migration_review", None)
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(current), job["job_id"]))
    return current


def proposal_for(store, job):
    reference = job.get("proposal_ref")
    if type(reference) is not dict:
        raise ContractError("No candidate proposal registered")
    with store.read_connection() as connection:
        row = connection.execute("SELECT body FROM details WHERE hash=?", (reference["digest"],)).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != reference["digest"]:
        raise ContractError("Candidate proposal missing or corrupted")
    value, _ = validate_proposal(job["repo"], loads(row[0]))
    if value["source_digest"] != job["assessment"]["source_digest"] or value["goal"] != job["goal"] or value["allowed_paths"] != reference["paths"]:
        raise ContractError("Stored candidate proposal has contradictory job bindings")
    return value


def candidate_for(store, job, policy):
    reference = job.get("candidate_ref")
    if type(reference) is not dict:
        raise ContractError("No engine-owned candidate exists")
    fields(reference, {"schema_version", "kind", "id", "job_id", "path", "source_digest", "candidate_digest", "proposal_digest", "changed_paths"}, "candidate reference")
    expected_path = policy.workspace / "candidates" / job["job_id"] / reference["id"]
    if reference["job_id"] != job["job_id"] or reference["path"] != str(expected_path):
        raise ContractError("Engine-owned candidate path/job binding corrupted")
    with store.read_connection() as connection:
        row = connection.execute("SELECT path,body,body_sha256 FROM candidates WHERE id=? AND job_id=?", (reference["id"], job["job_id"])).fetchone()
    if row is None or row[0] != str(expected_path) or hashlib.sha256(row[1]).hexdigest() != row[2] or loads(row[1]) != reference:
        raise ContractError("Engine-owned candidate receipt missing or corrupted")
    if reference["source_digest"] != job["assessment"]["source_digest"] or reference["proposal_digest"] != job["proposal_ref"]["digest"] or snapshot(expected_path)["digest"] != reference["candidate_digest"]:
        raise ContractError("Engine-owned candidate/source/proposal identity is stale")
    return reference


def build(store, job, policy):
    from .reviews import accepted
    from .runtime_lock import locked

    accepted(store, job, "contract", policy)
    accepted(store, job, "migration", policy)
    with locked(policy, job["job_id"]):
        return _build(store, store.get(job["job_id"]), policy)


def _build(store, job, policy):
    from .reviews import accepted

    accepted(store, job, "contract", policy)
    accepted(store, job, "migration", policy)
    if job["state"] != "MIGRATION_APPROVED":
        raise ContractError("A current reviewed migration and protected baseline are required")
    proposal = proposal_for(store, job)
    candidate_id = uuid.uuid4().hex
    destination = policy.workspace / "candidates" / job["job_id"] / candidate_id
    # Reserve the unique path and job state BEFORE touching source/candidate files.
    reservation = {"id": candidate_id, "job_id": job["job_id"], "path": str(destination), "state": "BUILDING", "proposal_digest": job["proposal_ref"]["digest"]}
    raw = dumps(reservation)
    with store.connection() as connection:
        current = _job(connection, job["job_id"], store.profile)
        if current["revision"] != job["revision"] or current["state"] != "MIGRATION_APPROVED":
            raise ContractError("Job changed or candidate already building")
        connection.execute("INSERT INTO candidates VALUES (?,?,?,?,?)", (candidate_id, job["job_id"], str(destination), raw, hashlib.sha256(raw).hexdigest()))
        current.update(state="CANDIDATE_BUILDING", candidate_reservation=reservation, revision=current["revision"] + 1)
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(current), job["job_id"]))
    try:
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        result = stage_candidate(Path(job["repo"]), destination, proposal)
        reference = {"schema_version": 1, "kind": "EngineCandidate", "id": candidate_id, "job_id": job["job_id"], "path": str(destination), "source_digest": result["source_digest"], "candidate_digest": result["candidate_digest"], "proposal_digest": result["proposal_digest"], "changed_paths": result["changed_paths"]}
        raw = dumps(reference)
        with store.connection() as connection:
            current = _job(connection, job["job_id"], store.profile)
            if current.get("candidate_reservation") != reservation or current["state"] != "CANDIDATE_BUILDING":
                raise ContractError("Candidate reservation changed; materialisation quarantined")
            connection.execute("UPDATE candidates SET body=?,body_sha256=? WHERE id=? AND job_id=?", (raw, hashlib.sha256(raw).hexdigest(), candidate_id, job["job_id"]))
            current.pop("candidate_reservation")
            current.update(candidate_ref=reference, state="CANDIDATE_BUILT", revision=current["revision"] + 1)
            connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(current), job["job_id"]))
        return current
    except BaseException:
        # Never delete or reuse partial output. A fresh decision/recovery is needed.
        with store.connection() as connection:
            current = _job(connection, job["job_id"], store.profile)
            if current.get("candidate_reservation") == reservation and current["state"] == "CANDIDATE_BUILDING":
                current.update(state="INTERRUPTED", revision=current["revision"] + 1, failure_reason="Candidate build interrupted; reserved residue retained, no automatic replay")
                connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(current), job["job_id"]))
        raise

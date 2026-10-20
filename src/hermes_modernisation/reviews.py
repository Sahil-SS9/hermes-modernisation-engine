"""Exact owner-review decisions, independent from process execution grants."""

import hashlib
import uuid

from .contracts import digest, fields
from .identity import snapshot
from .jsonio import ContractError, dumps, identifier

DECISION_FIELDS = {"schema_version", "kind", "job_id", "profile", "actor", "purpose", "source_digest", "oracle_digest", "proposal_digest", "allowed_paths"}


def validate_decision(value):
    fields(value, DECISION_FIELDS, "review decision")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "ReviewDecision" or value["purpose"] not in ("contract", "migration"):
        raise ContractError("Unsupported review decision")
    for key in ("job_id", "profile", "actor"):
        identifier(value[key])
    for key in ("source_digest", "oracle_digest"):
        digest(value[key])
    if value["purpose"] == "contract":
        if value["proposal_digest"] is not None:
            raise ContractError("Contract review cannot authorise a candidate proposal")
    else:
        digest(value["proposal_digest"])
    paths = value["allowed_paths"]
    if type(paths) is not list or not paths or len(paths) > 100 or any(type(path) is not str for path in paths) or len(set(paths)) != len(paths):
        raise ContractError("Exact reviewed output paths required")
    return value


def request(store, job, purpose, actor, profile):
    identifier(actor)
    contract = store.contract_for(job["job_id"])
    if purpose not in ("contract", "migration"):
        raise ContractError("Unsupported owner review purpose")
    proposal_digest = None
    if purpose == "migration":
        if not job.get("baseline_ref") or not job.get("proposal_ref") or job["state"] != "PLAN_REVIEW_REQUIRED":
            raise ContractError("Captured baseline and saved candidate proposal required")
        proposal_digest = job["proposal_ref"]["digest"]
    return {"decision": validate_decision({
        "schema_version": 1, "kind": "ReviewDecision", "job_id": job["job_id"],
        "profile": profile, "actor": actor, "purpose": purpose,
        "source_digest": job["assessment"]["source_digest"],
        "oracle_digest": job["behaviour_contract"]["digest"],
        "proposal_digest": proposal_digest, "allowed_paths": contract["allowed_paths"],
    }), "permission_granted": False, "execution_performed": False}


def accepted(store, job, purpose, policy):
    """Revalidate the private signed review and its durable consumed claim."""
    from .jsonio import loads

    reference = job.get(purpose + "_review")
    if type(reference) is not dict or reference.get("purpose") != purpose:
        raise ContractError("Authentic owner review required before this operation")
    with store.read_connection() as connection:
        row = connection.execute("SELECT purpose,body,body_sha256 FROM reviews WHERE id=? AND job_id=?", (reference["id"], job["job_id"])).fetchone()
    if row is None or row[0] != purpose or hashlib.sha256(row[1]).hexdigest() != row[2]:
        raise ContractError("Private owner review missing or corrupted")
    saved = loads(row[1])
    fields(saved, {"reference", "grant"}, "stored owner review")
    if saved["reference"] != reference:
        raise ContractError("Stored owner review has contradictory job bindings")
    decision = validate_decision(saved["grant"]["body"]["decision"])
    if any(decision[name] != reference[name] for name in DECISION_FIELDS) or decision["job_id"] != job["job_id"] or decision["profile"] != policy.profile or decision["oracle_digest"] != job["behaviour_contract"]["digest"] or decision["source_digest"] != job["assessment"]["source_digest"]:
        raise ContractError("Reviewed scope/profile/contract is stale")
    if purpose == "migration" and decision["proposal_digest"] != job.get("proposal_ref", {}).get("digest"):
        raise ContractError("Reviewed candidate proposal is stale")
    policy.authority().verify_recorded(saved["grant"], decision, "decision")
    return reference


def accept(store, job, grant, policy):
    from .state import _job

    if type(grant) is not dict or type(grant.get("body")) is not dict or type(grant["body"].get("decision")) is not dict:
        raise ContractError("Authentic signed review decision required")
    decision = validate_decision(grant["body"]["decision"])
    expected = request(store, job, decision["purpose"], decision["actor"], policy.profile)["decision"]
    if dumps(decision) != dumps(expected):
        raise ContractError("Owner review differs from current job/profile/contract/proposal")
    if snapshot(job["repo"])["digest"] != decision["source_digest"]:
        raise ContractError("Reviewed source is stale")
    # Authenticate before workspace creation or any job mutation.
    policy.authority().verify_review(grant, expected)
    authority = policy.authority(create=True)
    nonce = authority.claim_review(grant, expected)
    reference = {**decision, "id": uuid.uuid4().hex, "authenticated": True, "authority_nonce": nonce}
    raw = dumps({"reference": reference, "grant": grant})
    with store.connection() as connection:
        current = _job(connection, job["job_id"])
        if current["revision"] != job["revision"]:
            raise ContractError("Job changed during owner review; grant consumed, no automatic replay")
        purpose = decision["purpose"]
        connection.execute("INSERT INTO reviews VALUES (?,?,?,?,?)", (reference["id"], job["job_id"], purpose, raw, hashlib.sha256(raw).hexdigest()))
        current[purpose + "_review"] = reference
        current["revision"] += 1
        if purpose == "migration":
            current["state"] = "MIGRATION_APPROVED"
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(current), job["job_id"]))
    return current

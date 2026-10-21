"""Authenticated owner reviews of BusinessRule candidates.

The sealed lexical rule page stays candidate-only. A rule review is a separate
signed decision binding the exact rule digest; it records an owner assertion of
adequacy, never executed coverage. A page edit cannot mint a review.
"""

import hashlib
import uuid

from .contracts import bounded_text, digest, fields
from .identity import snapshot
from .jsonio import ContractError, dumps, loads, identifier

ADEQUACY = "owner-asserted-adequate"
DECISION_FIELDS = {
    "schema_version", "kind", "job_id", "profile", "actor", "purpose",
    "source_digest", "rule_id", "rule_digest", "adequacy",
}
REFERENCE_EXTRA = {"id", "authenticated", "authority_nonce"}


def validate_decision(value):
    fields(value, DECISION_FIELDS, "rule review decision")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported rule review version")
    if value["kind"] != "RuleReviewDecision" or value["purpose"] != "rule":
        raise ContractError("Unsupported rule review decision")
    for key in ("job_id", "profile", "actor", "rule_id"):
        identifier(value[key])
    for key in ("source_digest", "rule_digest"):
        digest(value[key])
    if value["adequacy"] != ADEQUACY:
        raise ContractError("Rule review cannot claim proved adequacy")
    return value


def _rule(store, job, rule_id):
    identifier(rule_id)
    if job["assessment"].get("rule_schema") != "business-rule-v1":
        raise ContractError("Rule review requires a current BusinessRule inventory")
    page = 0
    while page < 200:
        chunk = store.details(job["job_id"], "rules", page)
        for rule in chunk["items"]:
            if rule["id"] == rule_id:
                return rule
        if not chunk["has_more"]:
            break
        page += 1
    raise ContractError("Reviewed rule is not in the current inventory")


def rule_digest(rule):
    return hashlib.sha256(dumps(rule)).hexdigest()


def request(store, job, rule_id, actor, profile):
    identifier(actor)
    rule = _rule(store, job, rule_id)
    return {
        "decision": validate_decision({
            "schema_version": 1, "kind": "RuleReviewDecision", "job_id": job["job_id"],
            "profile": profile, "actor": actor, "purpose": "rule",
            "source_digest": job["assessment"]["source_digest"],
            "rule_id": rule["id"], "rule_digest": rule_digest(rule),
            "adequacy": ADEQUACY,
        }),
        "permission_granted": False,
        "execution_performed": False,
    }


def accept(store, job, grant, policy):
    if type(grant) is not dict or type(grant.get("body")) is not dict or type(grant["body"].get("decision")) is not dict:
        raise ContractError("Authentic signed rule review required")
    decision = validate_decision(grant["body"]["decision"])
    expected = request(store, job, decision["rule_id"], decision["actor"], policy.profile)["decision"]
    if dumps(decision) != dumps(expected):
        raise ContractError("Rule review differs from the current rule/profile")
    if snapshot(job["repo"])["digest"] != decision["source_digest"]:
        raise ContractError("Reviewed rule source is stale")
    policy.authority().verify_rule_review(grant, expected)
    nonce = policy.authority(create=True).claim_rule_review(grant, expected)
    reference = {**expected, "id": uuid.uuid4().hex, "authenticated": True, "authority_nonce": nonce}
    raw = dumps({"reference": reference, "grant": grant})
    with store.connection() as connection:
        connection.execute(
            "INSERT INTO reviews VALUES (?,?,?,?,?)",
            (reference["id"], job["job_id"], "rule", raw, hashlib.sha256(raw).hexdigest()),
        )
    return reference


def listing(store, job, policy):
    if job["assessment"].get("rule_schema") != "business-rule-v1":
        return {
            "schema_version": 1, "job_id": job["job_id"], "reviews": [],
            "coverage_status": "unverified", "permission_granted": False,
            "execution_performed": False,
        }
    with store.read_connection() as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] < 4:
            return {
                "schema_version": 1, "job_id": job["job_id"], "reviews": [],
                "coverage_status": "unverified", "permission_granted": False,
                "execution_performed": False,
            }
        rows = connection.execute(
            "SELECT id,body,body_sha256 FROM reviews WHERE job_id=? AND purpose='rule' ORDER BY rowid",
            (job["job_id"],),
        ).fetchall()
    authority = policy.authority()
    current = {}
    page = 0
    while page < 200:
        chunk = store.details(job["job_id"], "rules", page)
        for rule in chunk["items"]:
            current[rule["id"]] = rule_digest(rule)
        if not chunk["has_more"]:
            break
        page += 1
    reviews = []
    for row_id, raw, expected_sha in rows:
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ContractError("Stored rule review is corrupted")
        saved = loads(raw)
        fields(saved, {"reference", "grant"}, "stored rule review")
        reference = saved["reference"]
        fields(reference, DECISION_FIELDS | REFERENCE_EXTRA, "stored rule review reference")
        decision = validate_decision(saved["grant"]["body"]["decision"])
        if any(reference[key] != decision[key] for key in DECISION_FIELDS):
            raise ContractError("Stored rule review reference contradicts its signed decision")
        if reference["id"] != row_id or reference["authenticated"] is not True:
            raise ContractError("Stored rule review lacks an authenticated identity")
        bounded_text(reference["authority_nonce"], 500, "rule review authority nonce")
        if decision["job_id"] != job["job_id"] or decision["profile"] != policy.profile or decision["source_digest"] != job["assessment"]["source_digest"]:
            raise ContractError("Stored rule review is stale for this job/profile")
        authority.verify_recorded(saved["grant"], decision, "decision")
        reviews.append({
            **decision,
            "id": reference["id"],
            "authenticated": True,
            "authority_nonce": reference["authority_nonce"],
            "current_rule_digest": current.get(decision["rule_id"]),
        })
    return {
        "schema_version": 1,
        "job_id": job["job_id"],
        "reviews": reviews,
        "coverage_status": "unverified",
        "permission_granted": False,
        "execution_performed": False,
    }

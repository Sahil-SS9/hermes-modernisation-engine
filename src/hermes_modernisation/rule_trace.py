"""Authenticated rule citations and executed case-assertion trace.

A lexical candidate is never promoted by this module.  A rule only becomes
``reviewed`` from a re-verified owner RuleReview record whose sealed digest
still matches, and only becomes ``executed`` when stored observed cases link to
it.  Coverage stays unverified on any stale review, orphan link, missing phase
or failed response.
"""

from .contracts import fields
from .jsonio import ContractError, dumps, identifier
import hashlib

FIELDS = {
    "schema_version",
    "kind",
    "job_id",
    "source_digest",
    "oracle_digest",
    "rules",
    "coverage",
    "lexical_only",
    "reviewed",
    "executed",
    "failed",
    "orphan_links",
    "missing_evidence",
    "verdict",
    "execution_performed",
}
RULE_FIELDS = {
    "rule_id",
    "rule_digest",
    "source_refs",
    "status",
    "review_id",
    "reviewed_rule_digest",
    "cases",
    "gaps",
}
CASE_FIELDS = {"phase", "case_id", "matches_expected"}


def build(job, rules, reviews, evaluations):
    """Pure trace builder over sealed lexical rules, reviews and observations."""
    if type(job) is not dict:
        raise ContractError("Migration job required")
    rule_rows = []
    reviewed = {}
    stale = set()
    for review in reviews:
        rule_id = review["rule_id"]
        reviewed[rule_id] = review
        if review["rule_digest"] != review["current_rule_digest"]:
            stale.add(rule_id)
    known = set()
    cases_by_rule = {}
    for row in evaluations:
        phase = row["phase"]
        for case in row["evaluation"]["cases"]:
            for rule_id in case["rule_ids"]:
                cases_by_rule.setdefault(rule_id, []).append(
                    {
                        "phase": phase,
                        "case_id": case["id"],
                        "matches_expected": case["matches_expected"],
                    }
                )
    orphan = sorted(set(cases_by_rule) - {rule["id"] for rule in rules})
    executed_count = 0
    failed_count = 0
    for rule in rules:
        rule_id = identifier(rule["id"])
        known.add(rule_id)
        citations = [
            {
                "path": ref["path"],
                "line_start": ref["line_start"],
                "line_end": ref["line_end"],
                "sha256": ref["sha256"],
            }
            for ref in rule["source_refs"]
        ]
        links = cases_by_rule.get(rule_id, [])
        phases = {link["phase"] for link in links}
        review = reviewed.get(rule_id)
        gaps = []
        if review is None:
            status = "candidate_only"
            gaps.append("no authenticated owner rule review")
        elif rule_id in stale:
            status = "review_stale"
            gaps.append("sealed rule digest changed after review")
        elif not links:
            status = "reviewed_unexecuted"
            gaps.append("no executed observed case links to this rule")
        elif any(not link["matches_expected"] for link in links):
            status = "reviewed_failed"
            gaps.append("an executed linked case fails the protected oracle")
        elif not {"baseline", "candidate"} <= phases:
            status = "reviewed_partial"
            gaps.append("both observed phases are required for coverage")
        else:
            status = "reviewed_executed"
        if status == "reviewed_executed":
            executed_count += 1
        if status in {"reviewed_failed", "review_stale"}:
            failed_count += 1
        rule_rows.append(
            {
                "rule_id": rule_id,
                "rule_digest": hashlib.sha256(dumps(rule)).hexdigest(),
                "source_refs": citations,
                "status": status,
                "review_id": review["id"] if review else None,
                "reviewed_rule_digest": review["rule_digest"] if review else None,
                "cases": sorted(links, key=lambda link: (link["phase"], link["case_id"])),
                "gaps": gaps,
            }
        )
    if orphan:
        missing = ["Observed case links name rules absent from the current inventory"]
    else:
        missing = []
    if any(row["status"] != "reviewed_executed" for row in rule_rows):
        missing.append("Every current rule needs a fresh review and linked passing cases in both phases")
    if not rule_rows:
        missing.append("No current business-rule inventory exists")
    coverage = "verified" if rule_rows and not missing else "unverified"
    return {
        "schema_version": 1,
        "kind": "RuleTrace",
        "job_id": job["job_id"],
        "source_digest": job["assessment"]["source_digest"],
        "oracle_digest": job["behaviour_contract"]["digest"],
        "rules": rule_rows,
        "coverage": coverage,
        "lexical_only": any(row["status"] == "candidate_only" for row in rule_rows),
        "reviewed": sum(row["review_id"] is not None for row in rule_rows),
        "executed": executed_count,
        "failed": failed_count,
        "orphan_links": orphan,
        "missing_evidence": missing,
        "verdict": "NOT_PROVEN",
        "execution_performed": False,
    }


def validate_trace(value):
    fields(value, FIELDS, "rule trace")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "RuleTrace"
        or value["verdict"] != "NOT_PROVEN"
        or value["execution_performed"] is not False
    ):
        raise ContractError("Unsupported rule trace")
    identifier(value["job_id"])
    for key in ("source_digest", "oracle_digest"):
        if type(value[key]) is not str or len(value[key]) != 64:
            raise ContractError("Rule trace digest is invalid")
    if value["coverage"] not in {"verified", "unverified"}:
        raise ContractError("Unknown rule coverage state")
    if type(value["rules"]) is not list:
        raise ContractError("Rule trace rows must be a list")
    for row in value["rules"]:
        fields(row, RULE_FIELDS, "rule trace row")
        identifier(row["rule_id"])
        if row["status"] not in {
            "candidate_only",
            "review_stale",
            "reviewed_unexecuted",
            "reviewed_partial",
            "reviewed_failed",
            "reviewed_executed",
        }:
            raise ContractError("Unknown rule trace state")
        if type(row["source_refs"]) is not list or type(row["cases"]) is not list:
            raise ContractError("Invalid rule trace citations")
        for case in row["cases"]:
            fields(case, CASE_FIELDS, "rule trace case")
            if case["phase"] not in {"baseline", "candidate"} or type(case["matches_expected"]) is not bool:
                raise ContractError("Invalid rule trace case link")
    if value["coverage"] == "verified" and (
        not value["rules"]
        or any(row["status"] != "reviewed_executed" for row in value["rules"])
    ):
        raise ContractError("Verified coverage contradicts an incomplete rule row")
    return value


def trace(store, job, policy):
    from . import observations, rule_reviews

    pages = job["assessment"].get("detail_pages", {}).get("rules", [])
    if job["assessment"].get("rule_schema") != "business-rule-v1" or not pages:
        return validate_trace(
            {
                "schema_version": 1,
                "kind": "RuleTrace",
                "job_id": job["job_id"],
                "source_digest": job["assessment"]["source_digest"],
                "oracle_digest": job["behaviour_contract"]["digest"],
                "rules": [],
                "coverage": "unverified",
                "lexical_only": False,
                "reviewed": 0,
                "executed": 0,
                "failed": 0,
                "orphan_links": [],
                "missing_evidence": ["No current business-rule inventory exists"],
                "verdict": "NOT_PROVEN",
                "execution_performed": False,
            }
        )
    listing = rule_reviews.listing(store, job, policy)
    rules = []
    page = 0
    while page < 200:
        chunk = store.details(job["job_id"], "rules", page)
        rules.extend(chunk["items"])
        if not chunk["has_more"]:
            break
        page += 1
    evaluations = []
    if job.get("baseline_ref"):
        evaluations.append(
            {
                "phase": "baseline",
                "evaluation": observations.read_one(store, job, job["baseline_ref"], policy),
            }
        )
    if job.get("candidate_observation_ref"):
        evaluations.append(
            {
                "phase": "candidate",
                "evaluation": observations.read_one(
                    store, job, job["candidate_observation_ref"], policy
                ),
            }
        )
    return validate_trace(build(job, rules, listing["reviews"], evaluations))

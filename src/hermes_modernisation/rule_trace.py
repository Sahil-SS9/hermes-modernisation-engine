"""Authenticated rule citations and executed case-assertion trace.

A lexical candidate is never promoted by this module.  A rule only becomes
``reviewed`` from a re-verified owner RuleReview record whose sealed digest
still matches, and only becomes ``executed`` when stored observed cases link to
it.  Coverage stays unverified on any stale review, orphan link, missing phase
or failed response.
"""

from .contracts import digest, fields
from .identity import safe_relative
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
    if type(rules) is not list or type(reviews) is not list or type(evaluations) is not list:
        raise ContractError("Rule trace inputs must be lists")
    rule_rows = []
    reviewed = {}
    stale = set()
    for review in reviews:
        if type(review) is not dict or review.get("authenticated") is not True:
            raise ContractError("Rule review is not authenticated")
        for key in ("id", "rule_id", "rule_digest", "current_rule_digest"):
            if key not in review:
                raise ContractError("Rule review identity is incomplete")
        rule_id = identifier(review["rule_id"])
        identifier(review["id"])
        digest(review["rule_digest"])
        if review["current_rule_digest"] is not None:
            digest(review["current_rule_digest"])
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


def _trace_citation(value):
    fields(value, {"path", "line_start", "line_end", "sha256"}, "rule trace citation")
    safe_relative(value["path"])
    digest(value["sha256"])
    if any(type(value[key]) is not int for key in ("line_start", "line_end")):
        raise ContractError("Rule trace citation lines must be integers")
    if not 1 <= value["line_start"] <= value["line_end"] <= 1000000:
        raise ContractError("Rule trace citation lines are out of bounds")


def _trace_case(value):
    fields(value, CASE_FIELDS, "rule trace case")
    identifier(value["case_id"])
    if value["phase"] not in {"baseline", "candidate"}:
        raise ContractError("Invalid rule trace phase")
    if type(value["matches_expected"]) is not bool:
        raise ContractError("Invalid rule trace case result")


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
        digest(value[key])
    if value["coverage"] not in {"verified", "unverified"}:
        raise ContractError("Unknown rule coverage state")
    if type(value["lexical_only"]) is not bool:
        raise ContractError("Rule trace lexical flag must be boolean")
    rules = value["rules"]
    if type(rules) is not list or len(rules) > 10000:
        raise ContractError("Rule trace rows must be a bounded list")
    rule_ids = set()
    reviewed_count = 0
    executed_count = 0
    failed_count = 0
    lexical_only = False
    for row in rules:
        fields(row, RULE_FIELDS, "rule trace row")
        rule_id = identifier(row["rule_id"])
        if rule_id in rule_ids:
            raise ContractError("Duplicate rule trace identity")
        rule_ids.add(rule_id)
        digest(row["rule_digest"])
        status = row["status"]
        if status not in {
            "candidate_only",
            "review_stale",
            "reviewed_unexecuted",
            "reviewed_partial",
            "reviewed_failed",
            "reviewed_executed",
        }:
            raise ContractError("Unknown rule trace state")
        refs = row["source_refs"]
        if type(refs) is not list or not 1 <= len(refs) <= 20:
            raise ContractError("Rule trace citations must be bounded")
        for ref in refs:
            _trace_citation(ref)
        review_id = row["review_id"]
        reviewed_digest = row["reviewed_rule_digest"]
        if review_id is None:
            if reviewed_digest is not None or status != "candidate_only":
                raise ContractError("Review identity contradicts rule trace state")
        else:
            identifier(review_id)
            if reviewed_digest is None:
                raise ContractError("Reviewed rule digest required")
            digest(reviewed_digest)
            if status == "candidate_only":
                raise ContractError("Candidate row cannot carry a review identity")
            if status == "review_stale":
                if reviewed_digest == row["rule_digest"]:
                    raise ContractError("Stale review digest matches the current rule")
            elif reviewed_digest != row["rule_digest"]:
                raise ContractError("Reviewed rule digest does not match the current rule")
            reviewed_count += 1
        cases = row["cases"]
        if type(cases) is not list or len(cases) > 10000:
            raise ContractError("Rule trace cases must be a bounded list")
        seen_cases = set()
        phases = set()
        for case in cases:
            _trace_case(case)
            key = (case["phase"], case["case_id"])
            if key in seen_cases:
                raise ContractError("Duplicate rule trace case link")
            seen_cases.add(key)
            phases.add(case["phase"])
        if status == "reviewed_unexecuted" and cases:
            raise ContractError("Unexecuted rule cannot carry case links")
        if status in {"reviewed_partial", "reviewed_failed", "reviewed_executed"} and not cases:
            raise ContractError("Executed rule status requires case links")
        if status == "reviewed_partial" and (
            not phases or phases == {"baseline", "candidate"}
        ):
            raise ContractError("Partial rule must have exactly one observed phase")
        if status == "reviewed_failed" and all(
            case["matches_expected"] for case in cases
        ):
            raise ContractError("Failed rule must contain a failed case")
        if status == "reviewed_executed" and (
            phases != {"baseline", "candidate"}
            or not all(case["matches_expected"] for case in cases)
        ):
            raise ContractError("Executed rule needs both passing observed phases")
        gaps = row["gaps"]
        if type(gaps) is not list or any(
            type(gap) is not str or not 1 <= len(gap) <= 1000 for gap in gaps
        ):
            raise ContractError("Rule trace gaps must be bounded text")
        if status == "reviewed_executed":
            if gaps:
                raise ContractError("Executed rule cannot carry a coverage gap")
            executed_count += 1
        elif not gaps:
            raise ContractError("Unverified rule must disclose a coverage gap")
        if status in {"reviewed_failed", "review_stale"}:
            failed_count += 1
        if status == "candidate_only":
            lexical_only = True
    for key in ("reviewed", "executed", "failed"):
        if type(value[key]) is not int or value[key] < 0:
            raise ContractError("Rule trace counts must be non-negative integers")
    if value["reviewed"] != reviewed_count:
        raise ContractError("Rule trace reviewed count contradicts its rows")
    if value["executed"] != executed_count:
        raise ContractError("Rule trace executed count contradicts its rows")
    if value["failed"] != failed_count:
        raise ContractError("Rule trace failed count contradicts its rows")
    if value["lexical_only"] != lexical_only:
        raise ContractError("Rule trace lexical flag contradicts its rows")
    orphan_links = value["orphan_links"]
    if type(orphan_links) is not list:
        raise ContractError("Rule trace orphan links must be a list")
    seen_orphans = set()
    for rule_id in orphan_links:
        identifier(rule_id)
        if rule_id in seen_orphans or rule_id in rule_ids:
            raise ContractError("Rule trace orphan link is duplicated or known")
        seen_orphans.add(rule_id)
    missing = value["missing_evidence"]
    if type(missing) is not list or any(
        type(item) is not str or not 1 <= len(item) <= 1000 for item in missing
    ):
        raise ContractError("Rule trace missing evidence must be bounded text")
    if value["coverage"] == "verified":
        if (
            not rules
            or value["lexical_only"]
            or value["reviewed"] != len(rules)
            or value["executed"] != len(rules)
            or value["failed"]
            or orphan_links
            or missing
            or any(row["status"] != "reviewed_executed" for row in rules)
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

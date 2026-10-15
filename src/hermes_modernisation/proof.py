"""Partial proof policy: report concrete data differences, never mint assurance.

A consumer-supplied receipt object is UNAUTHENTICATED. This pure evaluator
therefore never returns SAME_WITHIN_CONTRACT; trusted receipt acceptance and
protected controls must be implemented separately before that verdict exists.
"""

from .compare import compare_cases
from .jsonio import ContractError, dumps, loads
from .store import identifier

FIELDS = {
    "schema_version",
    "required_cases",
    "required_rules",
    "rule_cases",
    "scope",
    "planned_differences",
}


def evaluate_pair(contract, before, after, old_cases, new_cases):
    contract = loads(dumps(contract))
    before = loads(dumps(before))
    after = loads(dumps(after))
    if (
        set(contract) != FIELDS
        or type(contract["schema_version"]) is not int
        or contract["schema_version"] != 1
    ):
        raise ContractError("Invalid behavioural scope contract")
    if type(contract["scope"]) is not str or not 1 <= len(contract["scope"]) <= 4000:
        raise ContractError("Explicit bounded scope required")
    if contract["planned_differences"] != []:
        raise ContractError("Signed planned differences not implemented")
    required = contract["required_cases"]
    rules = contract["required_rules"]
    mapping = contract["rule_cases"]
    for items in (required, rules):
        if (
            type(items) is not list
            or len(items) > 1000
            or len(set(items)) != len(items)
        ):
            raise ContractError("Invalid case/rule list")
        for item in items:
            identifier(item)
    if not required:
        raise ContractError("Empty required case set cannot establish parity")
    if type(mapping) is not dict or set(mapping) != set(rules):
        raise ContractError("Every required rule needs an explicit case mapping")
    for cases in mapping.values():
        if type(cases) is not list or not cases or not set(cases) <= set(required):
            raise ContractError("Invalid rule-to-case mapping")
    compared = compare_cases(old_cases, new_cases)
    old_ids = {case["id"] for case in old_cases}
    new_ids = {case["id"] for case in new_cases}
    gaps = [
        "receipt objects have not been authenticated by a protected acceptance service",
        "protected oracle independence, rule adequacy and mutation controls are unverified",
    ]
    usable = True
    for receipt, phase in ((before, "baseline"), (after, "candidate")):
        if (
            receipt.get("phase") != phase
            or type(receipt.get("process_exit_code")) is not int
            or receipt["process_exit_code"] != 0
        ):
            usable = False
        if any(
            receipt.get(flag) is not False for flag in ("timed_out", "truncated")
        ) or any(
            receipt.get(flag) is not True
            for flag in ("container_removed", "source_unchanged")
        ):
            usable = False
    if before.get("oracle_digest") != after.get("oracle_digest"):
        usable = False
        gaps.append("old/new oracle identities differ")
    complete = old_ids == new_ids == set(required)
    if not complete:
        gaps.append("required case identities absent or unexpected cases present")
    if not usable:
        gaps.append("collection incomplete, failed or identity-mismatched")
    verdict = "DIFFERS" if compared["differs"] and usable and complete else "NOT_PROVEN"
    by_id = {row["id"]: row["verdict"] for row in compared["cases"]}
    statuses = {
        rule: (
            "matched-data-not-proven"
            if usable and all(by_id.get(case) == "same" for case in cases)
            else "not-proven"
        )
        for rule, cases in mapping.items()
    }
    return {
        "schema_version": 1,
        "scope": contract["scope"],
        "verdict": verdict,
        "provenance": "untrusted-receipt-data-only",
        "matched_cases": compared["same"],
        "different_cases": compared["differs"],
        "collection_usable": usable,
        "required_case_set_complete": complete,
        "rule_status": statuses,
        "missing_evidence": gaps,
        "execution_performed": False,
        "approved_differences": [],
    }

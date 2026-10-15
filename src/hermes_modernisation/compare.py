"""Deterministic data comparator. Data equality is never execution proof."""

import re
from .jsonio import ContractError, dumps
from .store import identifier

FIELDS = {"id", "input_digest", "output", "exception", "side_effects"}


def _index(cases):
    if type(cases) is not list or len(cases) > 1000:
        raise ContractError("Cases must be a bounded list")
    result = {}
    for case in cases:
        if type(case) is not dict or set(case) != FIELDS:
            raise ContractError(
                "Invalid case fields; unapproved masking/tolerances unavailable"
            )
        identifier(case["id"])
        if case["id"] in result:
            raise ContractError("Duplicate case identity")
        if type(case["input_digest"]) is not str or not re.fullmatch(
            r"[a-f0-9]{64}", case["input_digest"]
        ):
            raise ContractError("Invalid case input digest")
        if type(case["side_effects"]) is not list:
            raise ContractError("Side effects must be explicit")
        dumps(case)
        result[case["id"]] = case
    return result


def compare_cases(old, new):
    before = _index(old)
    after = _index(new)
    records = []
    for key in sorted(set(before) | set(after)):
        a = before.get(key)
        b = after.get(key)
        if a is None or b is None:
            records.append({"id": key, "verdict": "missing"})
            continue
        if a["input_digest"] != b["input_digest"]:
            raise ContractError("Old/new inputs differ")
        records.append(
            {"id": key, "verdict": "same" if dumps(a) == dumps(b) else "differs"}
        )
    same = sum(x["verdict"] == "same" for x in records)
    differs = sum(x["verdict"] == "differs" for x in records)
    missing = sum(x["verdict"] == "missing" for x in records)
    # Positive and mutation controls exercise the same canonical equality primitive.
    self_check = (
        dumps({"control": 1}) == dumps({"control": 1})
        and dumps({"control": 1}) != dumps({"control": True})
        and dumps({"control": "a"}) != dumps({"control": "b"})
    )
    return {
        "schema_version": 1,
        "verdict": "NOT_PROVEN",
        "provenance": "data-comparison-only",
        "same": same,
        "differs": differs,
        "missing": missing,
        "cases": records,
        "self_check_passed": self_check,
        "execution_performed": False,
        "missing_evidence": [
            "authenticated trusted execution receipts and current source/oracle identities",
            "independent protected oracle adequacy and required case coverage",
        ],
    }

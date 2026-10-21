"""Actual response-boundary mutants against the unchanged protected oracle.

These are deterministic behavioural controls, not source-code mutations and not
execution proof.  Each mutant changes a real observed response collection and
must be detected by re-evaluating it through the same oracle.  A weakened
collection (missing/extra/reordered cases, or a failing original) is disclosed
and can never report verified mutation coverage.
"""

import hashlib

from .baseline import evaluate_response, wire_id
from .contracts import fields
from .jsonio import ContractError, dumps, identifier

FIELDS = {
    "schema_version",
    "kind",
    "job_id",
    "attempt_id",
    "source_digest",
    "oracle_digest",
    "mutants",
    "total",
    "detected",
    "undetected",
    "coverage",
    "integrity",
    "missing_evidence",
    "verdict",
    "execution_performed",
}
MUTANT_FIELDS = {
    "mutant_id",
    "case_id",
    "mutation",
    "detected",
    "outcome",
    "detail",
}
MAX_CASES = 12


def _response(contract, attempt_id, outputs):
    results = []
    for index, output in enumerate(outputs):
        case_id = (
            contract["cases"][index]["id"]
            if index < len(contract["cases"])
            else "__mutant_extra__"
        )
        results.append({"id": wire_id(attempt_id, case_id), "output": output})
    return dumps({"schema_version": 1, "results": results})


def _detect(contract, attempt_id, outputs, case_id, mutation):
    try:
        evaluation = evaluate_response(contract, attempt_id, _response(contract, attempt_id, outputs))
    except (ContractError, ValueError) as error:
        return True, "refused", str(error)[:300]
    failures = [
        case["id"] for case in evaluation["cases"] if not case["matches_expected"]
    ]
    if case_id is not None and case_id in failures:
        return True, "mismatch", "mutated case fails the unchanged oracle"
    if mutation == "reordered":
        return bool(failures), "mismatch" if failures else "undetected", "reorder changed oracle outcome"
    return bool(failures), "mismatch" if failures else "undetected", "oracle compared the mutant"


def build(job, contract, evaluation, attempt_id):
    identifier(attempt_id)
    expected_ids = [case["id"] for case in contract["cases"]]
    observed_ids = [case["id"] for case in evaluation["cases"]]
    integrity = "exact" if expected_ids == observed_ids else "weakened"
    outputs = [case["output"] for case in evaluation["cases"]]
    if len(outputs) != len(contract["cases"]):
        integrity = "weakened"
        outputs = outputs[: len(contract["cases"])]
    original_ok = integrity == "exact" and evaluation["failed"] == 0
    mutants = []
    selected = list(range(min(len(outputs), MAX_CASES)))
    for index in selected:
        case_id = contract["cases"][index]["id"]
        mutated = list(outputs)
        mutated[index] = {"__mutant__": hashlib.sha256(case_id.encode()).hexdigest()[:16]}
        detected, outcome, detail = _detect(
            contract, attempt_id, mutated, case_id, "value"
        )
        mutants.append(
            {
                "mutant_id": "value-" + hashlib.sha256(case_id.encode()).hexdigest()[:12],
                "case_id": case_id,
                "mutation": "value",
                "detected": detected,
                "outcome": outcome,
                "detail": detail,
            }
        )
    if len(outputs) >= 2:
        swapped = list(outputs)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        detected, outcome, detail = _detect(
            contract, attempt_id, swapped, None, "reordered"
        )
        mutants.append(
            {
                "mutant_id": "reordered",
                "case_id": None,
                "mutation": "reordered",
                "detected": detected,
                "outcome": outcome,
                "detail": detail,
            }
        )
    omitted = list(outputs[:-1])
    detected, outcome, detail = _detect(
        contract, attempt_id, omitted, None, "omitted"
    )
    mutants.append(
        {
            "mutant_id": "omitted",
            "case_id": None,
            "mutation": "omitted",
            "detected": detected,
            "outcome": outcome,
            "detail": detail,
        }
    )
    extra = list(outputs) + [{"__mutant__": "extra"}]
    detected, outcome, detail = _detect(contract, attempt_id, extra, None, "extra")
    mutants.append(
        {
            "mutant_id": "extra",
            "case_id": None,
            "mutation": "extra",
            "detected": detected,
            "outcome": outcome,
            "detail": detail,
        }
    )
    undetected = sum(not mutant["detected"] for mutant in mutants)
    missing = []
    if integrity != "exact":
        missing.append("Observed case collection differs from the sealed contract")
    if not original_ok:
        missing.append("Original observed collection did not pass the unchanged oracle")
    if undetected:
        missing.append("One or more behavioural mutants were not detected")
    if not mutants:
        missing.append("No response cases were available for mutant controls")
    if len(outputs) > MAX_CASES:
        missing.append(
            f"Mutant controls sampled {MAX_CASES} of {len(outputs)} observed cases"
        )
    return validate(
        {
            "schema_version": 1,
            "kind": "MutantReceipt",
            "job_id": job["job_id"],
            "attempt_id": attempt_id,
            "source_digest": job["assessment"]["source_digest"],
            "oracle_digest": job["behaviour_contract"]["digest"],
            "mutants": mutants,
            "total": len(mutants),
            "detected": len(mutants) - undetected,
            "undetected": undetected,
            "coverage": "verified" if mutants and not missing else "unverified",
            "integrity": integrity,
            "missing_evidence": missing,
            "verdict": "NOT_PROVEN",
            "execution_performed": False,
        }
    )


def validate(value):
    fields(value, FIELDS, "behavioural mutant receipt")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "MutantReceipt"
        or value["verdict"] != "NOT_PROVEN"
        or value["execution_performed"] is not False
    ):
        raise ContractError("Unsupported behavioural mutant receipt")
    identifier(value["job_id"])
    identifier(value["attempt_id"])
    if value["coverage"] not in {"verified", "unverified"}:
        raise ContractError("Unknown mutant coverage")
    if value["integrity"] not in {"exact", "weakened"}:
        raise ContractError("Unknown mutant integrity")
    if type(value["mutants"]) is not list or len(value["mutants"]) > 64:
        raise ContractError("Bounded mutant list required")
    detected_count = 0
    undetected_count = 0
    for mutant in value["mutants"]:
        fields(mutant, MUTANT_FIELDS, "behavioural mutant")
        if type(mutant["detected"]) is not bool:
            raise ContractError("Strict mutant detection flag required")
        if mutant["mutation"] not in {"value", "reordered", "omitted", "extra"}:
            raise ContractError("Unknown mutant kind")
        if mutant["outcome"] not in {"mismatch", "refused", "undetected"}:
            raise ContractError("Unknown mutant outcome")
        if mutant["detected"] != (mutant["outcome"] != "undetected"):
            raise ContractError("Mutant outcome contradicts its detection flag")
        if mutant["detected"]:
            detected_count += 1
        else:
            undetected_count += 1
    if type(value["total"]) is not int or value["total"] < 0:
        raise ContractError("Mutant total must be a non-negative integer")
    if type(value["detected"]) is not int or value["detected"] < 0:
        raise ContractError("Detected mutant count must be a non-negative integer")
    if type(value["undetected"]) is not int or value["undetected"] < 0:
        raise ContractError("Undetected mutant count must be a non-negative integer")
    if value["total"] != len(value["mutants"]):
        raise ContractError("Mutant total contradicts its receipts")
    if value["detected"] != detected_count or value["undetected"] != undetected_count:
        raise ContractError("Mutant counts do not reconcile")
    if value["detected"] + value["undetected"] != value["total"]:
        raise ContractError("Mutant counts do not reconcile")
    missing = value["missing_evidence"]
    if type(missing) is not list or any(
        type(item) is not str or not 1 <= len(item) <= 1000 for item in missing
    ):
        raise ContractError("Bounded mutant missing-evidence notes required")
    if value["coverage"] == "verified" and (
        value["undetected"]
        or value["integrity"] != "exact"
        or not value["mutants"]
        or value["detected"] != value["total"]
        or missing
    ):
        raise ContractError("Verified mutant coverage contradicts its receipts")
    return value

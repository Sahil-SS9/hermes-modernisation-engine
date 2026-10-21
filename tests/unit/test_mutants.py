"""Real response-boundary mutants must be detected by the unchanged oracle."""

import pytest

from hermes_modernisation.baseline import evaluate_response
from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.mutants import build, validate


def fixture():
    contract = {
        "scope": "declared_pure_json_response",
        "cases": [
            {
                "id": "fresh_0",
                "kind": "fresh",
                "input": {"value": 1},
                "expected": {"value": 2},
                "rule_ids": ["double"],
            },
            {
                "id": "fresh_1",
                "kind": "fresh",
                "input": {"value": 2},
                "expected": {"value": 4},
                "rule_ids": ["double"],
            },
        ],
    }
    job = {
        "job_id": "job",
        "assessment": {"source_digest": "a" * 64},
        "behaviour_contract": {"digest": "b" * 64},
    }
    attempt = "attempt"
    from hermes_modernisation.baseline import wire_id

    raw = dumps(
        {
            "schema_version": 1,
            "results": [
                {"id": wire_id(attempt, "fresh_0"), "output": {"value": 2}},
                {"id": wire_id(attempt, "fresh_1"), "output": {"value": 4}},
            ],
        }
    )
    evaluation = evaluate_response(contract, attempt, raw)
    assert evaluation["failed"] == 0
    return job, contract, evaluation, attempt


def test_value_reorder_omission_and_extra_mutants_are_detected():
    job, contract, evaluation, attempt = fixture()
    receipt = build(job, contract, evaluation, attempt)
    validate(receipt)
    assert receipt["integrity"] == "exact"
    assert receipt["total"] >= 5
    assert receipt["undetected"] == 0
    assert receipt["coverage"] == "verified"
    assert {mutant["mutation"] for mutant in receipt["mutants"]} == {
        "value",
        "reordered",
        "omitted",
        "extra",
    }


def test_weakened_case_collection_never_verifies():
    job, contract, evaluation, attempt = fixture()
    evaluation["cases"] = evaluation["cases"][:1]
    receipt = build(job, contract, evaluation, attempt)
    assert receipt["integrity"] == "weakened"
    assert receipt["coverage"] == "unverified"
    assert any("differs" in gap for gap in receipt["missing_evidence"])


def test_large_case_collection_is_not_silently_sampled_as_verified():
    job, contract, _, attempt = fixture()
    contract["cases"] = [
        {
            "id": f"fresh_{index}",
            "kind": "fresh",
            "input": {"value": index},
            "expected": {"value": index * 2},
            "rule_ids": ["double"],
        }
        for index in range(20)
    ]
    from hermes_modernisation.baseline import wire_id

    raw = dumps(
        {
            "schema_version": 1,
            "results": [
                {"id": wire_id(attempt, case["id"]), "output": case["expected"]}
                for case in contract["cases"]
            ],
        }
    )
    evaluation = evaluate_response(contract, attempt, raw)
    receipt = build(job, contract, evaluation, attempt)
    assert receipt["total"] == 15
    assert receipt["coverage"] == "unverified"
    assert any("14 of 20" in gap or "12 of 20" in gap for gap in receipt["missing_evidence"])


def test_receipt_cannot_claim_verified_with_missing_evidence_or_contradictory_outcome():
    job, contract, evaluation, attempt = fixture()
    receipt = build(job, contract, evaluation, attempt)
    assert receipt["coverage"] == "verified"
    receipt["missing_evidence"] = ["undeclared gap"]
    with pytest.raises(ContractError):
        validate(receipt)
    receipt = build(job, contract, evaluation, attempt)
    receipt["mutants"][0]["outcome"] = "undetected"
    with pytest.raises(ContractError):
        validate(receipt)

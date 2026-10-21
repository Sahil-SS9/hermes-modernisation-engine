"""Real response-boundary mutants must be detected by the unchanged oracle."""

from hermes_modernisation.baseline import evaluate_response
from hermes_modernisation.jsonio import dumps
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

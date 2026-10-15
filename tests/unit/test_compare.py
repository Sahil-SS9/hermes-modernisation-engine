import pytest
from hermes_modernisation.compare import compare_cases
from hermes_modernisation.jsonio import ContractError


def case(value):
    return {
        "id": "case-one",
        "input_digest": "a" * 64,
        "output": value,
        "exception": None,
        "side_effects": [],
    }


def test_outputs_errors_types_and_side_effects():
    assert compare_cases([case({"value": 1})], [case({"value": 1})])["same"] == 1
    assert compare_cases([case({"value": 1})], [case({"value": True})])["differs"] == 1
    assert compare_cases([case("abc")], [case("abd")])["differs"] == 1
    changed = case("abc")
    changed["exception"] = {"type": "ValueError", "message": "invalid"}
    assert compare_cases([case("abc")], [changed])["differs"] == 1
    changed = case("abc")
    changed["side_effects"] = [{"file": "result", "digest": "b" * 64}]
    assert compare_cases([case("abc")], [changed])["differs"] == 1


def test_empty_duplicate_missing_cases_and_mask_abuse():
    result = compare_cases([], [])
    assert result["same"] == 0 and result["missing_evidence"]
    assert compare_cases([case("x")], [])["missing"] == 1
    changed = case("x")
    changed["input_digest"] = "b" * 64
    with pytest.raises(ContractError):
        compare_cases([case("x")], [changed])
    with pytest.raises(ContractError):
        compare_cases([case("x"), case("x")], [case("x")])
    changed = case("x")
    changed["mask"] = ".*"
    with pytest.raises(ContractError):
        compare_cases([case("x")], [changed])


def test_healthy_data_does_not_claim_execution_proof():
    result = compare_cases([case("x")], [case("x")])
    assert result["verdict"] == "NOT_PROVEN"
    assert result["provenance"] == "data-comparison-only"
    assert result["self_check_passed"]

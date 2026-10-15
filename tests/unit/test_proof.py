"""Private boundary tests: a PASS string or caller-authored JSON is not proof."""

import pytest
from hermes_modernisation.proof import evaluate_pair
from hermes_modernisation.jsonio import ContractError


def case(output):
    return {
        "id": "one",
        "input_digest": "a" * 64,
        "output": output,
        "exception": None,
        "side_effects": [],
    }


def fixture():
    contract = {
        "schema_version": 1,
        "required_cases": ["one"],
        "required_rules": ["rule-one"],
        "rule_cases": {"rule-one": ["one"]},
        "scope": "double function only",
        "planned_differences": [],
    }
    receipt = {
        "schema_version": 1,
        "source_digest": "a" * 64,
        "oracle_digest": "b" * 64,
        "image": "fixture@sha256:" + "c" * 64,
        "phase": "baseline",
        "process_exit_code": 0,
        "timed_out": False,
        "truncated": False,
        "container_removed": True,
        "source_unchanged": True,
        "grade": "observed-process-only",
        "missing_evidence": ["receipt ingestion not authenticated"],
    }
    after = dict(receipt, phase="candidate", source_digest="d" * 64)
    return contract, receipt, after


def test_data_equality_never_upgrades_untrusted_receipts():
    contract, old, new = fixture()
    result = evaluate_pair(contract, old, new, [case(4)], [case(4)])
    assert result["verdict"] == "NOT_PROVEN" and result["matched_cases"] == 1
    assert result["missing_evidence"]
    assert result["rule_status"]["rule-one"] == "matched-data-not-proven"


@pytest.mark.parametrize(
    "field,value",
    [
        ("truncated", True),
        ("timed_out", True),
        ("process_exit_code", 1),
        ("container_removed", False),
        ("source_unchanged", False),
    ],
)
def test_bad_collection_cannot_be_treated_as_same(field, value):
    contract, old, new = fixture()
    new[field] = value
    result = evaluate_pair(contract, old, new, [case(4)], [case(4)])
    assert result["verdict"] == "NOT_PROVEN" and result["collection_usable"] is False


def test_missing_cases_changed_behaviour_and_oracle_mismatch():
    contract, old, new = fixture()
    assert evaluate_pair(contract, old, new, [case(4)], [])["verdict"] == "NOT_PROVEN"
    assert (
        evaluate_pair(contract, old, new, [case(4)], [case(5)])["verdict"] == "DIFFERS"
    )
    new["oracle_digest"] = "e" * 64
    assert (
        evaluate_pair(contract, old, new, [case(4)], [case(4)])["verdict"]
        == "NOT_PROVEN"
    )


def test_empty_scope_and_unknown_approval_flags_refused():
    contract, old, new = fixture()
    contract["required_cases"] = []
    with pytest.raises(ContractError):
        evaluate_pair(contract, old, new, [], [])
    contract, old, new = fixture()
    contract["approved"] = True
    with pytest.raises(ContractError):
        evaluate_pair(contract, old, new, [case(4)], [case(4)])

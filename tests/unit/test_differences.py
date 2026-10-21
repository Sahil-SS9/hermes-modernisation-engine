"""Typed contract normalisations and observed comparison disclosure."""

import pytest

from hermes_modernisation.differences import (
    apply_to_case,
    validate_approved,
    validate_entries,
)
from hermes_modernisation.jsonio import ContractError


def contract(*entries):
    return {"normalizations": list(entries)}


def test_typed_operations_apply_to_a_deep_copy():
    value = {"msg": "  hello  ", "n": 1.236, "temporary": True, "nested": {"x": 1}}
    normalised, applied = apply_to_case(
        contract(
            {
                "case_id": "c",
                "operations": [
                    {"op": "trim", "path": "msg"},
                    {"op": "round", "path": "n", "digits": 2},
                    {"op": "drop", "path": "temporary"},
                ],
            }
        ),
        "c",
        value,
    )
    assert normalised == {"msg": "hello", "n": 1.24, "nested": {"x": 1}}
    assert value == {"msg": "  hello  ", "n": 1.236, "temporary": True, "nested": {"x": 1}}
    assert [item["op"] for item in applied] == ["trim", "round", "drop"]


def test_missing_or_wrongly_typed_fields_fail_closed():
    with pytest.raises(ContractError, match="absent"):
        apply_to_case(
            contract({"case_id": "c", "operations": [{"op": "trim", "path": "nope"}]}),
            "c",
            {"msg": "x"},
        )
    with pytest.raises(ContractError, match="string"):
        apply_to_case(
            contract({"case_id": "c", "operations": [{"op": "trim", "path": "n"}]}),
            "c",
            {"n": 1},
        )
    with pytest.raises(ContractError, match="number"):
        apply_to_case(
            contract({"case_id": "c", "operations": [{"op": "round", "path": "n", "digits": 1}]}),
            "c",
            {"n": "1"},
        )


@pytest.mark.parametrize(
    "entry",
    [
        {"case_id": "c", "operations": [{"op": "regex", "path": "x"}]},
        {"case_id": "c", "operations": [{"op": "trim", "path": "*"}]},
        {"case_id": "c", "operations": [{"op": "trim", "path": "x.y.z.q.r"}]},
        {"case_id": "c", "operations": [{"op": "round", "path": "x", "digits": 7}]},
        {
            "case_id": "c",
            "operations": [
                {"op": "trim", "path": "x"},
                {"op": "lowercase", "path": "x"},
            ],
        },
    ],
)
def test_broad_overlapping_or_unknown_masks_are_refused(entry):
    with pytest.raises(ContractError):
        validate_entries([entry], {"c"})


def test_approved_difference_shape_is_bounded():
    validate_approved([{"case_id": "c", "operations": [{"op": "lowercase", "path": "x"}]}])
    with pytest.raises(ContractError, match="Duplicate"):
        validate_approved(
            [
                {"case_id": "c", "operations": [{"op": "trim", "path": "x"}]},
                {"case_id": "c", "operations": [{"op": "trim", "path": "y"}]},
            ]
        )


def test_observed_comparison_discloses_only_contract_sealed_differences(tmp_path, monkeypatch):
    from test_behaviour_contract import contract_fixture
    from hermes_modernisation import observations
    from hermes_modernisation.baseline import evaluate_response, wire_id
    from hermes_modernisation.jsonio import dumps

    engine, job, contract = contract_fixture(tmp_path)
    contract["normalizations"] = [
        {"case_id": "malformed", "operations": [{"op": "trim", "path": "error"}]}
    ]
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    job = engine.invoke("status", {"job": job["job_id"]})

    def raw(attempt, changed):
        results = []
        for case in contract["cases"]:
            output = case["expected"]
            if changed and case["id"] == "malformed":
                output = {"error": " invalid "}
            results.append({"id": wire_id(attempt, case["id"]), "output": output})
        return dumps({"schema_version": 1, "results": results})

    baseline = evaluate_response(contract, "baseline_attempt", raw("baseline_attempt", False))
    candidate = evaluate_response(contract, "candidate_attempt", raw("candidate_attempt", True))
    assert baseline["failed"] == 0 and candidate["failed"] == 0
    evaluations = {"baseline_attempt": baseline, "candidate_attempt": candidate}
    monkeypatch.setattr(
        observations,
        "read_one",
        lambda store, job, ref, policy: evaluations[ref["attempt_id"]],
    )
    reference = {
        "schema_version": 1,
        "kind": "ObservationReference",
        "sha256": "c" * 64,
        "oracle_digest": job["behaviour_contract"]["digest"],
        "source_digest": job["assessment"]["source_digest"],
        "grade": "independently-observed-json-process-response",
    }
    job["baseline_ref"] = {
        **reference,
        "attempt_id": "baseline_attempt",
        "phase": "baseline",
        "passed": baseline["passed"],
        "failed": baseline["failed"],
    }
    job["candidate_observation_ref"] = {
        **reference,
        "attempt_id": "candidate_attempt",
        "phase": "candidate",
        "passed": candidate["passed"],
        "failed": candidate["failed"],
    }
    comparison = observations.comparison(engine.store, job, None)
    assert comparison["approved_differences"] == [
        {
            "case_id": "malformed",
            "operations": [{"op": "trim", "path": "error"}],
        }
    ]
    assert next(row for row in comparison["cases"] if row["id"] == "malformed")["same_output"] is True
    from hermes_modernisation.evidence_contracts import validate_comparison

    validate_comparison(comparison)

"""Trusted per-case evaluation and planted-mutation controls (M4.1 / M5.1 slice).

Every planted change to an otherwise accepted run must be refused or reported
as a difference. Acceptance is per-case reporting only, never PROVEN.
"""

import base64
import hashlib
import json

import pytest

from hermes_modernisation.evaluator import (
    GRADE,
    compare_evaluations,
    evaluate_output,
    load_expectation,
)
from hermes_modernisation.jsonio import ContractError

CASES = [["tests.unit.test_api", f"test_{n}"] for n in range(5)] + [
    ["tests.security.test_auth.TestAuth", "test_rejects"]
]
SUMMARY = "========== 6 passed, 1 warning in 0.50s =========="
WARN = (
    "============== warnings summary ==============\n"
    "lib.py:1\n  DeprecationWarning: demo\n\n-- Docs: https://docs.pytest.org"
)


def expectation(cases=CASES):
    return load_expectation(
        json.dumps(
            {"schema_version": 1, "kind": "junit-per-case", "skip_policy": "none", "cases": cases}
        ).encode()
    )


def junit(rows, extra=""):
    body = "".join(
        f'<testcase classname="{c}" name="{n}" time="0.01">{inner}</testcase>' for c, n, inner in rows
    )
    return (
        f'<?xml version="1.0" encoding="utf-8"?>{extra}<testsuites>'
        f'<testsuite name="pytest" tests="{len(rows)}">{body}</testsuite></testsuites>'
    ).encode()


def passing(cases=CASES):
    return [(c, n, "") for c, n in cases]


def output(rows=None, *, raw=None, status=0, summary=SUMMARY, counts=None, printed="", sha=None, size=None):
    raw = junit(passing() if rows is None else rows) if raw is None else raw
    if counts is None:
        text = raw.decode()
        counts = {
            "collected": text.count("<testcase"),
            "failures": text.count("<failure"),
            "errors": text.count("<error"),
            "skipped": text.count("<skipped"),
        }
    lines = [
        "============ test session starts ============",
        printed,
        WARN,
        summary,
        f"RUNNER_PYTEST_STATUS={status}",
        "RUNNER_COUNTS_JSON=" + json.dumps(counts, sort_keys=True),
        "RUNNER_ENV_JSON=" + json.dumps({"python": "3.14.8"}),
        f"RUNNER_JUNIT_BYTES={len(raw) if size is None else size}",
        "RUNNER_JUNIT_SHA256=" + (sha or hashlib.sha256(raw).hexdigest()),
        "RUNNER_JUNIT_BEGIN",
        base64.b64encode(raw).decode(),
        "RUNNER_JUNIT_END",
    ]
    return ("\n".join(lines) + "\n").encode()


# --- expectation contract -------------------------------------------------


def test_expectation_rejects_duplicates_unknown_fields_and_empty_sets():
    with pytest.raises(ContractError):
        expectation(CASES + [CASES[0]])
    with pytest.raises(ContractError):
        expectation([])
    with pytest.raises(ContractError):
        load_expectation(b'{"schema_version":1,"kind":"junit-per-case","skip_policy":"none","cases":[["a","b"]],"mask":"*"}')
    with pytest.raises(ContractError):
        load_expectation(b'{"schema_version":1,"kind":"junit-per-case","skip_policy":"some","cases":[["a","b"]]}')
    with pytest.raises(ContractError):
        load_expectation(b'{"schema_version":1,"schema_version":1,"kind":"junit-per-case","skip_policy":"none","cases":[["a","b"]]}')


# --- positive control -----------------------------------------------------


def test_accepts_exact_expected_passing_run_and_never_claims_proof():
    result = evaluate_output(output(), expectation())
    assert result["accepted"] is True, result["problems"]
    assert result["grade"] == GRADE and result["proof"] == "NOT_PROVEN"
    assert result["derived_counts"] == {"collected": 6, "failures": 0, "errors": 0, "skipped": 0}
    assert result["warnings_count"] == 1
    assert len(result["cases"]) == 6


# --- planted mutations: each must be refused ------------------------------


def _flip(index, inner):
    rows = passing()
    rows[index] = (rows[index][0], rows[index][1], inner)
    return rows


MUTANTS = {
    "one_failure": dict(rows=_flip(2, '<failure message="x">boom</failure>'), status=1, summary="== 1 failed, 5 passed in 0.5s =="),
    "one_error": dict(rows=_flip(2, '<error message="x">boom</error>'), status=1, summary="== 5 passed, 1 error in 0.5s =="),
    "one_skipped": dict(rows=_flip(0, '<skipped message="s"/>'), summary="== 5 passed, 1 skipped in 0.5s =="),
    "all_skipped": dict(rows=[(c, n, '<skipped message="s"/>') for c, n in CASES], summary="== 6 skipped in 0.5s =="),
    "zero_tests": dict(rows=[], status=5, summary="== no tests ran in 0.1s =="),
    "missing_case": dict(rows=passing(CASES[:5]), summary="== 5 passed in 0.5s =="),
    "extra_case": dict(rows=passing(CASES + [["tests.unit.test_api", "test_injected"]]), summary="== 7 passed in 0.5s =="),
    "substituted_case_same_count": dict(rows=passing(CASES[:5] + [["tests.unit.test_api", "test_impostor"]])),
    "duplicate_case": dict(rows=passing(CASES + [CASES[0]]), summary="== 7 passed in 0.5s =="),
    "nonzero_status_all_green": dict(status=1),
    "summary_disagrees": dict(summary="== 5 passed in 0.5s =="),
    "inflated_counts_line": dict(counts={"collected": 7, "failures": 0, "errors": 0, "skipped": 0}),
    "sha_forged": dict(sha="0" * 64),
    "length_forged": dict(size=1),
    "doctype_entity": dict(raw=junit(passing(), extra='<!DOCTYPE x [<!ENTITY a "b">]>')),
    "not_xml": dict(raw=b"definitely not xml"),
    "empty_junit": dict(raw=b""),
    "marker_injection": dict(printed="RUNNER_JUNIT_BEGIN\nAAAA\nRUNNER_JUNIT_END"),
    "duplicate_status_line": dict(printed="RUNNER_PYTEST_STATUS=0"),
}


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_planted_mutation_is_refused(name):
    result = evaluate_output(output(**MUTANTS[name]), expectation())
    assert result["accepted"] is False, name
    assert result["problems"], name


def test_non_utf8_and_oversized_output_refused():
    assert evaluate_output(b"\xff\xfe", expectation())["accepted"] is False
    big = junit(passing()) + b"<!--" + b"x" * (1024 * 1024) + b"-->"
    assert evaluate_output(output(raw=big), expectation())["accepted"] is False


def test_evaluate_output_rejects_non_bytes_input():
    with pytest.raises(ContractError):
        evaluate_output("text", expectation())


# --- before/after comparison ---------------------------------------------


def test_compare_same_selected_scope_reports_warning_delta():
    before = evaluate_output(output(), expectation())
    after_raw = output(summary="========== 6 passed, 3 warnings in 0.50s ==========")
    after = evaluate_output(after_raw, expectation())
    result = compare_evaluations(before, after)
    assert result["verdict"] == "SAME_SELECTED_SCOPE"
    assert result["proof"] == "NOT_PROVEN"
    assert result["warnings"] == {"before": 1, "after": 3, "delta": 2}
    assert all(row["verdict"] == "same" for row in result["cases"])


def test_compare_names_the_case_that_changed():
    before = evaluate_output(output(), expectation())
    after = evaluate_output(output(**MUTANTS["one_failure"]), expectation())
    result = compare_evaluations(before, after)
    assert result["verdict"] == "REFUSED_UNACCEPTED_EVIDENCE"
    changed = [row for row in result["cases"] if row["verdict"] != "same"]
    assert changed == [
        {"case": CASES[2], "before": "passed", "after": "failure", "verdict": "differs"}
    ]


def test_compare_refuses_mismatched_expectations():
    before = evaluate_output(output(), expectation())
    other = evaluate_output(output(rows=passing(CASES[:5]), summary="== 5 passed in 0.5s =="), expectation(CASES[:5]))
    with pytest.raises(ContractError):
        compare_evaluations(before, other)


def test_compare_refuses_caller_edited_evaluation():
    before = evaluate_output(output(), expectation())
    forged = json.loads(json.dumps(before))
    forged["cases"][0]["outcome"] = "failure"
    with pytest.raises(ContractError):
        compare_evaluations(before, forged)

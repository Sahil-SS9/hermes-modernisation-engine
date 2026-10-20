"""Response protocol metadata and draft bindings; no reported pass assertion is trusted."""

import hashlib

from hermes_modernisation.jsonio import dumps
from hermes_modernisation.runtime import environment_spec
from hermes_modernisation.service import Engine
from test_attempt_state import prepared_fixture


def test_public_response_protocol_exposes_only_request_and_response_data(tmp_path):
    result = Engine(tmp_path / "private").invoke("response_protocol", {})
    assert result["protocol"] == "json-batch-v1"
    assert result["request_case_fields"] == ["id", "input"]
    assert result["response_case_fields"] == ["id", "output"]
    assert result["execution_performed"] is False
    assert result["expected_values_sent"] is False


def test_prepared_operation_binds_exact_protected_inputs_without_expected_values(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    prepared = engine.invoke("prepare", args)
    contract = engine.store.contract_for(job["job_id"])
    payload = dumps({"schema_version": 1, "cases": [
        {"id": hashlib.sha256((prepared["attempt_id"] + ":" + case["id"]).encode()).hexdigest(), "input": case["input"]}
        for case in contract["cases"]
    ]})
    environment = environment_spec(prepared["operation"], contract["runtimes"]["baseline"]["image"], "baseline", hashlib.sha256(payload).hexdigest())
    assert prepared["operation"]["environment_digest"] == hashlib.sha256(dumps(environment)).hexdigest()


def response_fixture(tmp_path):
    from hermes_modernisation.baseline import wire_id

    engine, job, _ = prepared_fixture(tmp_path)
    contract = engine.store.contract_for(job["job_id"])
    aid = "owned_attempt"
    data = {"schema_version": 1, "results": [{"id": wire_id(aid, case["id"]), "output": case["expected"]} for case in contract["cases"]]}
    return contract, aid, data


def test_matching_response_bytes_are_not_execution_proof(tmp_path):
    from hermes_modernisation.baseline import evaluate_response

    contract, aid, data = response_fixture(tmp_path)
    result = evaluate_response(contract, aid, dumps(data))
    assert result["passed"] == result["collected"] == result["expected"] == 12
    assert result["provenance"] == "data-comparison-only"
    assert result["verdict"] == "NOT_PROVEN"
    data["results"][0]["output"] = {"value": 999}
    altered = evaluate_response(contract, aid, dumps(data))
    assert altered["failed"] == 1 and altered["passed"] == 11


def test_expected_values_and_rule_links_never_enter_input_payload(tmp_path):
    from hermes_modernisation.baseline import make_inputs
    from hermes_modernisation.jsonio import loads

    contract, aid, _ = response_fixture(tmp_path)
    contract["cases"][0]["expected"] = {"private_expected_canary": "must_not_leave_controller"}
    payload = make_inputs(contract, aid)
    assert b"private_expected_canary" not in payload
    assert all(set(case) == {"id", "input"} for case in loads(payload)["cases"])


def test_forged_junit_counts_duplicate_or_reordered_results_are_refused(tmp_path):
    from copy import deepcopy
    import pytest
    from hermes_modernisation.baseline import evaluate_response
    from hermes_modernisation.jsonio import ContractError

    contract, aid, good = response_fixture(tmp_path)
    values = [b'<testsuite tests="12" failures="0"/>', dumps({"schema_version": True, "results": good["results"]}), dumps({**good, "passed": 12})]
    for change in ("missing", "duplicate", "reordered", "asserted_pass"):
        value = deepcopy(good)
        if change == "missing":
            value["results"].pop()
        elif change == "duplicate":
            value["results"][1]["id"] = value["results"][0]["id"]
        elif change == "reordered":
            value["results"].reverse()
        else:
            value["results"][0]["passed"] = True
        values.append(dumps(value))
    for raw in values:
        with pytest.raises(ContractError):
            evaluate_response(contract, aid, raw)

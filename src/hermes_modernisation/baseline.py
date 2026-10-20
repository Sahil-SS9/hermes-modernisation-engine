"""Protected JSON process-response inputs and external value evaluation.

The app receives inputs and opaque correlation IDs, never expected values,
rule links or a test harness. Parsing bytes alone is data comparison, NOT an
observed receipt; only the trusted capture path may correlate real execution.
The supported contract covers process JSON responses, not hidden DB/files.
"""

import hashlib
import os
import stat
from pathlib import Path

from .contracts import fields, input_digest
from .jsonio import ContractError, dumps, loads, MAX_BYTES


def protocol():
    return {
        "schema_version": 1, "protocol": "json-batch-v1",
        "request_fields": ["schema_version", "cases"],
        "request_case_fields": ["id", "input"],
        "response_fields": ["schema_version", "results"],
        "response_case_fields": ["id", "output"],
        "response_order": "exact request order; no missing, duplicate or extra IDs",
        "max_json_bytes": MAX_BYTES, "max_cases": 500,
        "expected_values_sent": False, "execution_performed": False,
        "provenance": "protocol-description-only", "verdict": "NOT_PROVEN",
    }


def wire_id(attempt_id, case_id):
    return hashlib.sha256((attempt_id + ":" + case_id).encode()).hexdigest()


def make_inputs(contract, attempt_id):
    return dumps({"schema_version": 1, "cases": [
        {"id": wire_id(attempt_id, case["id"]), "input": case["input"]}
        for case in contract["cases"]
    ]})


def evaluate_response(contract, attempt_id, raw):
    """Pure parser/matcher. Caller-supplied bytes never establish execution."""
    value = loads(raw)
    fields(value, {"schema_version", "results"}, "process response")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported response protocol version")
    results = value["results"]
    cases = contract["cases"]
    if type(results) is not list or len(results) != len(cases) or not cases:
        raise ContractError("Expected response collection does not match")
    evaluated = []
    for case, result in zip(cases, results, strict=True):
        fields(result, {"id", "output"}, "process response case")
        if result["id"] != wire_id(attempt_id, case["id"]):
            raise ContractError("Missing, duplicate, extra or reordered response identity")
        matches = dumps({"value": result["output"]}) == dumps({"value": case["expected"]})
        evaluated.append({
            "id": case["id"], "kind": case["kind"], "input_digest": input_digest(case["input"]),
            "output": result["output"], "matches_expected": matches, "rule_ids": case["rule_ids"],
        })
    passed = sum(case["matches_expected"] for case in evaluated)
    return {
        "schema_version": 1, "kind": "ResponseEvaluation", "scope": contract["scope"],
        "expected": len(cases), "collected": len(evaluated), "passed": passed,
        "failed": len(evaluated) - passed, "errors": 0, "skipped": 0,
        "cases": evaluated, "provenance": "data-comparison-only", "verdict": "NOT_PROVEN",
        "missing_evidence": ["authentic independently captured execution", "reviewed rule adequacy and behavioural mutation controls"],
        "unobserved_effects": ["filesystem", "database", "network", "unexposed internal state"],
    }


def read_artifact(path, maximum):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > maximum:
            raise ContractError("Unsafe or oversized private capture artifact")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise ContractError("Private capture artifact exceeds bound")
        return raw
    finally:
        os.close(descriptor)


def capture(executor, grant, operation, source, oracle, contract):
    """Trusted controller-only collector; not a public import/record endpoint.

    Its caller constructs the real configured Executor; candidate code and
    proposal data cannot select a collector or supply accepted receipt bytes.
    """
    payload = make_inputs(contract, operation["attempt_id"])
    if executor.input_data != payload or hashlib.sha256(dumps(contract)).hexdigest() != operation["oracle_digest"]:
        raise ContractError("Protected inputs/oracle differ from exact operation")
    receipt = executor.run(grant, operation, source, oracle)
    folder = executor.root / operation["attempt_id"]
    stored = loads(read_artifact(folder / "receipt.json", MAX_BYTES))
    if dumps(stored) != dumps(receipt):
        raise ContractError("Executor receipt readback differs")
    for name in ("job_id", "attempt_id", "profile", "source_digest", "oracle_digest", "environment_digest"):
        if receipt.get(name) != operation[name]:
            raise ContractError("Capture receipt has contradictory operation bindings")
    if receipt.get("phase") != executor.phase or receipt.get("image") != executor.image:
        raise ContractError("Capture phase/image differs")
    if type(receipt.get("process_exit_code")) is not int or receipt["process_exit_code"] != 0 or any(receipt.get(key) is not False for key in ("timed_out", "truncated")) or any(receipt.get(key) is not True for key in ("container_removed", "source_unchanged", "input_complete")):
        raise ContractError("Process capture incomplete, failed or cleanup/source unverified")
    if receipt.get("input_sha256") != hashlib.sha256(payload).hexdigest() or receipt.get("input_bytes") != len(payload):
        raise ContractError("Captured input transport differs")
    raw = read_artifact(folder / "output.bin", operation["output_limit_bytes"])
    if len(raw) != receipt["output_bytes"] or hashlib.sha256(raw).hexdigest() != receipt["output_sha256"]:
        raise ContractError("Captured process output changed")
    evaluation = evaluate_response(contract, operation["attempt_id"], raw)
    return {
        "schema_version": 1, "kind": "ProtectedCapture", "phase": executor.phase,
        "job_id": operation["job_id"], "attempt_id": operation["attempt_id"],
        "operation": operation, "receipt": receipt, "evaluation": evaluation,
        "capture_origin": "trusted-executor-direct-return-and-private-readback",
        "raw_output_sha256": receipt["output_sha256"], "artifact_root": str(folder),
        "verdict": "NOT_PROVEN", "execution_performed": True,
    }

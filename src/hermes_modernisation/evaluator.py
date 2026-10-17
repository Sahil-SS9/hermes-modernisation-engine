"""Trusted per-case test evidence evaluator and before/after comparison.

Runs on the operator side over a run's retained output bytes; it never executes
repository code. The in-sandbox program prints its raw JUnit XML base64-encoded
between single BEGIN/END markers with byte length and SHA-256. Everything here
is re-derived from those bytes and fails closed on ambiguity.

The JUnit bytes are still authored inside the sandbox that ran the tested code,
so acceptance means "the exact expected cases were REPORTED as passing". It is
never proof: every result carries proof NOT_PROVEN. The evaluation digest is an
integrity check against accidental or naive edits, not authentication.
"""

import base64
import binascii
import hashlib
import re
import xml.etree.ElementTree as ET

from .jsonio import ContractError, dumps, loads

GRADE = "candidate-authored-per-case-junit"
PROGRAM_PROTOCOL = "junit-stdout-v1"
MAX_OUTPUT_BYTES = 4194304
MAX_JUNIT_BYTES = 1048576
MAX_CASES = 5000
MAX_WARNING_LINES = 200
_EXPECTATION_FIELDS = {"schema_version", "kind", "skip_policy", "cases"}
_NAME = re.compile(r"[A-Za-z0-9_.\[\]\-:/ ]{1,300}")
_SUMMARY = re.compile(r"^=+ (?P<body>.+?) in [0-9.]+s(?: \([^)]*\))? =+$")
_SUMMARY_KEYS = {"warning": "warnings", "error": "errors"}


def load_expectation(raw):
    """Parse a predeclared exact testcase set (duplicate-free canonical JSON)."""
    data = loads(raw)
    if type(data) is not dict or set(data) != _EXPECTATION_FIELDS:
        raise ContractError("Unknown or missing expectation fields")
    if data["schema_version"] != 1 or data["kind"] != "junit-per-case":
        raise ContractError("Unsupported expectation version/kind")
    if data["skip_policy"] != "none":
        raise ContractError("Only the zero-skip policy is implemented")
    cases = data["cases"]
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        raise ContractError("Expectation needs a bounded non-empty case list")
    seen = set()
    for case in cases:
        if (
            type(case) is not list
            or len(case) != 2
            or not all(type(part) is str and _NAME.fullmatch(part) for part in case)
        ):
            raise ContractError("Malformed expected case identity")
        if tuple(case) in seen:
            raise ContractError("Duplicate expected case identity")
        seen.add(tuple(case))
    return {
        "schema_version": 1,
        "kind": "junit-per-case",
        "skip_policy": "none",
        "cases": [list(case) for case in cases],
        "digest": hashlib.sha256(dumps(data)).hexdigest(),
    }


def _single(lines, prefix):
    found = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    if len(found) != 1:
        raise ValueError(f"expected exactly one {prefix!r} line, found {len(found)}")
    return found[0]


def _outcome(case):
    tags = {child.tag for child in case}
    kinds = [tag for tag in ("failure", "error", "skipped") if tag in tags]
    return "+".join(kinds) if kinds else "passed"


def _summary(lines):
    matches = [m for m in (_SUMMARY.match(line.strip()) for line in lines) if m]
    if not matches:
        return None, None
    body = matches[-1].group("body")
    parts = {}
    for item in body.split(", "):
        count, _, key = item.partition(" ")
        if count.isdigit() and key:
            parts[_SUMMARY_KEYS.get(key, key)] = int(count)
    return body, parts


def _warning_lines(lines):
    out, inside = [], False
    for line in lines:
        if line.startswith("=") and "warnings summary" in line:
            inside = True
            continue
        if inside and (line.startswith("-- Docs:") or line.startswith("=")):
            break
        if inside:
            out.append(line)
    return out[:MAX_WARNING_LINES]


def _seal(result):
    body = {key: value for key, value in result.items() if key != "evaluation_sha256"}
    return hashlib.sha256(dumps(body)).hexdigest()


def _finish(result):
    result["accepted"] = not result["problems"]
    result["evaluation_sha256"] = _seal(result)
    return result


def evaluate_output(output, expectation):
    """Evaluate retained run output against the exact expected case set."""
    if type(output) is not bytes:
        raise ContractError("Run output must be bytes")
    expected = [tuple(case) for case in expectation["cases"]]
    result = {
        "schema_version": 1,
        "protocol": PROGRAM_PROTOCOL,
        "grade": GRADE,
        "proof": "NOT_PROVEN",
        "expectation_digest": expectation["digest"],
        "expected_count": len(expected),
        "accepted": False,
        "problems": [],
        "cases": [],
    }
    if len(output) > MAX_OUTPUT_BYTES:
        result["problems"].append("run output exceeds bound")
        return _finish(result)
    try:
        lines = output.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        result["problems"].append("run output is not valid UTF-8")
        return _finish(result)
    try:
        status = int(_single(lines, "RUNNER_PYTEST_STATUS="))
        declared_bytes = int(_single(lines, "RUNNER_JUNIT_BYTES="))
        declared_sha = _single(lines, "RUNNER_JUNIT_SHA256=")
        reported = loads(_single(lines, "RUNNER_COUNTS_JSON=").encode())
        environment = loads(_single(lines, "RUNNER_ENV_JSON=").encode())
        begins = [i for i, line in enumerate(lines) if line == "RUNNER_JUNIT_BEGIN"]
        ends = [i for i, line in enumerate(lines) if line == "RUNNER_JUNIT_END"]
        if len(begins) != 1 or len(ends) != 1 or ends[0] != begins[0] + 2:
            raise ValueError("JUnit block must be exactly BEGIN, one base64 line, END")
        junit = base64.b64decode(lines[begins[0] + 1], validate=True)
    except (ValueError, binascii.Error, ContractError) as error:
        result["problems"].append(f"malformed runner output: {error}")
        return _finish(result)
    result.update(
        pytest_status=status,
        reported_counts=reported,
        runner_environment=environment,
        junit_bytes=len(junit),
        junit_sha256=hashlib.sha256(junit).hexdigest(),
    )
    if len(junit) != declared_bytes or result["junit_sha256"] != declared_sha:
        result["problems"].append("JUnit bytes do not match declared length/SHA-256")
    if not junit or len(junit) > MAX_JUNIT_BYTES:
        result["problems"].append("JUnit missing or exceeds bound")
        return _finish(result)
    lowered = junit.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        result["problems"].append("JUnit contains DOCTYPE/ENTITY; refused")
        return _finish(result)
    try:
        root = ET.fromstring(junit)
    except ET.ParseError as error:
        result["problems"].append(f"JUnit XML parse error: {error}")
        return _finish(result)
    cases = [
        {"case": [node.get("classname", ""), node.get("name", "")], "outcome": _outcome(node)}
        for node in root.iter("testcase")
    ][: MAX_CASES + 1]
    observed = [tuple(case["case"]) for case in cases]
    derived = {
        "collected": len(cases),
        "failures": sum("failure" in case["outcome"] for case in cases),
        "errors": sum("error" in case["outcome"] for case in cases),
        "skipped": sum("skipped" in case["outcome"] for case in cases),
    }
    duplicates = sorted({case for case in observed if observed.count(case) > 1})
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    summary_line, summary_counts = _summary(lines)
    result.update(
        cases=cases,
        derived_counts=derived,
        duplicates=[list(case) for case in duplicates],
        missing=[list(case) for case in missing],
        unexpected=[list(case) for case in unexpected],
        pytest_summary_line=summary_line,
        pytest_summary_counts=summary_counts,
        warnings_count=(summary_counts or {}).get("warnings", 0),
        warning_lines=_warning_lines(lines),
    )
    problems = result["problems"]
    if reported != derived:
        problems.append("reported counts differ from trusted re-derivation")
    if duplicates:
        problems.append("duplicate testcase identities")
    if missing or unexpected:
        problems.append("observed testcase set differs from expectation")
    if any(case["outcome"] != "passed" for case in cases):
        problems.append("one or more testcases did not pass")
    if status != 0:
        problems.append("test process status non-zero")
    if summary_counts is None or summary_counts.get("passed") != len(expected) or any(
        summary_counts.get(key) for key in ("failed", "errors", "skipped", "xfailed", "xpassed")
    ):
        problems.append("terminal summary does not report exactly the expected passes")
    return _finish(result)


def _checked(evaluation):
    evaluation = loads(dumps(evaluation))
    if evaluation.get("evaluation_sha256") != _seal(evaluation):
        raise ContractError("Evaluation was altered after evaluation")
    return evaluation


def compare_evaluations(before, after):
    """Per-case before/after comparison of two evaluations of one expectation."""
    before = _checked(before)
    after = _checked(after)
    if before["expectation_digest"] != after["expectation_digest"]:
        raise ContractError("Evaluations use different expectations")
    old = {tuple(case["case"]): case["outcome"] for case in before["cases"]}
    new = {tuple(case["case"]): case["outcome"] for case in after["cases"]}
    rows = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        verdict = "missing" if a is None or b is None else ("same" if a == b else "differs")
        rows.append({"case": list(key), "before": a, "after": b, "verdict": verdict})
    if not (before["accepted"] and after["accepted"]):
        verdict = "REFUSED_UNACCEPTED_EVIDENCE"
    elif all(row["verdict"] == "same" for row in rows):
        verdict = "SAME_SELECTED_SCOPE"
    else:
        verdict = "DIFFERS"
    warnings_before = before.get("warnings_count", 0)
    warnings_after = after.get("warnings_count", 0)
    return {
        "schema_version": 1,
        "verdict": verdict,
        "proof": "NOT_PROVEN",
        "grade": GRADE,
        "expectation_digest": before["expectation_digest"],
        "before_accepted": before["accepted"],
        "after_accepted": after["accepted"],
        "cases": rows,
        "warnings": {
            "before": warnings_before,
            "after": warnings_after,
            "delta": warnings_after - warnings_before,
        },
        "missing_evidence": [
            "results are authored inside the sandbox that ran the tested code",
            "selected-scope regression only; not behavioural equivalence",
        ],
    }

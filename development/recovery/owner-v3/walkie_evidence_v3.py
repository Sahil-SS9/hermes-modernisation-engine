"""Trusted per-case evidence evaluator for the v3 walkie regression trial.

Operator-only control code: runs on the host, outside every container, over the
retained executor output.bin. Stdlib only. It never executes repository code.

The in-container program prints the raw JUnit XML base64-encoded between
single BEGIN/END markers, with its byte length and SHA-256. This module
re-derives everything from those bytes and fails closed on any ambiguity.

Evidence grade: the JUnit bytes are still authored inside the container that
ran the tested code. Acceptance here proves the declared per-case regression
scope was REPORTED as passing with exact identities; it is not independent
authenticated proof or behavioural equivalence.
"""

import base64
import binascii
import hashlib
import json
import re
import xml.etree.ElementTree as ET

PROGRAM_VERSION = "walkie-junit-stdout-v3"
MAX_JUNIT_BYTES = 1048576
MAX_WARNING_LINES = 200
SUMMARY_RE = re.compile(r"^=+ (?P<body>.+?) in [0-9.]+s(?: \([^)]*\))? =+$")
GRADE = "candidate-authored-per-case-junit"


def load_expected(raw):
    data = json.loads(raw)
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported expected-cases version")
    cases = [tuple(case) for case in data["cases"]]
    if any(len(case) != 2 or not all(isinstance(part, str) and part for part in case) for case in cases):
        raise ValueError("Malformed expected case")
    if len(set(cases)) != len(cases):
        raise ValueError("Duplicate expected case")
    return cases


def _single(lines, prefix):
    found = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    if len(found) != 1:
        raise ValueError(f"Expected exactly one {prefix!r} line, found {len(found)}")
    return found[0]


def _outcome(case):
    tags = [child.tag for child in case]
    kinds = [tag for tag in ("failure", "error", "skipped") if tag in tags]
    if not kinds:
        return "passed"
    return "+".join(kinds)


def _summary(lines):
    matches = [SUMMARY_RE.match(line.strip()) for line in lines]
    matches = [match for match in matches if match]
    if not matches:
        return None, None
    body = matches[-1].group("body")
    parts = {}
    for item in body.split(", "):
        bits = item.split(" ", 1)
        if len(bits) == 2 and bits[0].isdigit():
            key = bits[1]
            key = {"warning": "warnings", "error": "errors"}.get(key, key)
            parts[key] = int(bits[0])
    return body, parts


def _warning_lines(lines):
    out, inside = [], False
    for line in lines:
        if "warnings summary" in line and line.startswith("="):
            inside = True
            continue
        if inside and (line.startswith("-- Docs:") or SUMMARY_RE.match(line.strip()) or line.startswith("=")):
            break
        if inside:
            out.append(line)
    return out[:MAX_WARNING_LINES]


def evaluate(output, expected_cases):
    """Return (evaluation dict, junit bytes or None). Never raises on bad input."""
    expected = [tuple(case) for case in expected_cases]
    result = {
        "schema_version": 1,
        "program_version": PROGRAM_VERSION,
        "grade": GRADE,
        "accepted": False,
        "problems": [],
        "expected_count": len(expected),
    }
    junit = None
    try:
        text = output.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        result["problems"].append("output is not valid UTF-8")
        return result, None
    lines = text.splitlines()
    try:
        status = int(_single(lines, "RUNNER_PYTEST_STATUS="))
        declared_bytes = int(_single(lines, "RUNNER_JUNIT_BYTES="))
        declared_sha = _single(lines, "RUNNER_JUNIT_SHA256=")
        reported_counts = json.loads(_single(lines, "RUNNER_COUNTS_JSON="))
        environment = json.loads(_single(lines, "RUNNER_ENV_JSON="))
        begins = [i for i, line in enumerate(lines) if line == "RUNNER_JUNIT_BEGIN"]
        ends = [i for i, line in enumerate(lines) if line == "RUNNER_JUNIT_END"]
        if len(begins) != 1 or len(ends) != 1 or ends[0] != begins[0] + 2:
            raise ValueError("JUnit block must be exactly BEGIN, one base64 line, END")
        junit = base64.b64decode(lines[begins[0] + 1], validate=True)
    except (ValueError, binascii.Error, json.JSONDecodeError) as error:
        result["problems"].append(f"malformed runner output: {error}")
        return result, None
    result.update(
        pytest_status=status,
        reported_counts=reported_counts,
        runner_environment=environment,
        junit_bytes=len(junit),
        junit_sha256=hashlib.sha256(junit).hexdigest(),
    )
    if len(junit) != declared_bytes or result["junit_sha256"] != declared_sha:
        result["problems"].append("JUnit bytes do not match declared length/SHA-256")
    if not junit or len(junit) > MAX_JUNIT_BYTES:
        result["problems"].append("JUnit missing or exceeds bound")
        return result, (junit or None)
    lowered = junit.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        result["problems"].append("JUnit contains DOCTYPE/ENTITY; refused")
        return result, junit
    try:
        root = ET.fromstring(junit)
    except ET.ParseError as error:
        result["problems"].append(f"JUnit XML parse error: {error}")
        return result, junit
    cases = []
    for case in root.iter("testcase"):
        cases.append(
            {
                "classname": case.get("classname", ""),
                "name": case.get("name", ""),
                "outcome": _outcome(case),
                "time": case.get("time"),
            }
        )
    observed = [(case["classname"], case["name"]) for case in cases]
    derived = {
        "collected": len(cases),
        "failures": sum("failure" in case["outcome"] for case in cases),
        "errors": sum("error" in case["outcome"] for case in cases),
        "skipped": sum("skipped" in case["outcome"] for case in cases),
    }
    duplicates = sorted({case for case in observed if observed.count(case) > 1})
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    not_passed = [case for case in cases if case["outcome"] != "passed"]
    summary_line, summary_counts = _summary(lines)
    result.update(
        cases=cases,
        derived_counts=derived,
        duplicates=[list(case) for case in duplicates],
        missing=[list(case) for case in missing],
        unexpected=[list(case) for case in unexpected],
        not_passed=not_passed,
        pytest_summary_line=summary_line,
        pytest_summary_counts=summary_counts,
        warnings_count=(summary_counts or {}).get("warnings", 0),
        warning_lines=_warning_lines(lines),
    )
    if reported_counts != derived:
        result["problems"].append("in-container counts differ from trusted re-derivation")
    if duplicates:
        result["problems"].append("duplicate testcase identities")
    if missing or unexpected:
        result["problems"].append("observed testcase set differs from predeclared set")
    if not_passed:
        result["problems"].append("one or more testcases did not pass")
    if status != 0:
        result["problems"].append("pytest exit status non-zero")
    if summary_counts is None or summary_counts.get("passed") != len(expected) or any(
        summary_counts.get(key) for key in ("failed", "errors", "skipped", "xfailed", "xpassed")
    ):
        result["problems"].append("pytest terminal summary does not report exactly the expected passes")
    result["accepted"] = not result["problems"]
    return result, junit

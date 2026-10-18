"""Public evidence workflow behaviour: retained run output is recorded through
the engine service, evaluated by the trusted evaluator, persisted in a
versioned store, and consumed by read-only compare/report.

Imported caller-authored data must never become authenticated proof: every
recorded result keeps grade candidate-authored-per-case-junit and proof
NOT_PROVEN, and invalid/stale/cross-job/tampered data fails closed.
"""

import base64
import hashlib
import json

import pytest

from hermes_modernisation.jsonio import ContractError
from hermes_modernisation.service import Engine

CASES = [
    ["test_app", "test_convert"],
    ["test_app", "test_authenticate_accepts_and_refuses"],
    ["test_app", "test_record_event_records_and_counts"],
]
SUMMARY = "= 3 passed, 1 warning in 0.30s =="
WARN_LINES = (
    "============== warnings summary ==============\n"
    "app.py:1\n  DeprecationWarning: fixture demo\n\n"
    "-- Docs: https://docs.pytest.org"
)


def expectation(cases=CASES):
    return {
        "schema_version": 1,
        "kind": "junit-per-case",
        "skip_policy": "none",
        "cases": [list(case) for case in cases],
    }


def junit(rows):
    body = "".join(
        f'<testcase classname="{c}" name="{n}" time="0.01">{inner}</testcase>'
        for c, n, inner in rows
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?><testsuites>'
        f'<testsuite name="pytest" tests="{len(rows)}">{body}</testsuite></testsuites>'
    ).encode()


def passing():
    return [(case[0], case[1], "") for case in CASES]


def output(rows=None, *, status=0, counts=None, sha=None, size=None):
    raw = junit(passing() if rows is None else rows)
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
        WARN_LINES,
        SUMMARY,
        f"RUNNER_PYTEST_STATUS={status}",
        "RUNNER_COUNTS_JSON=" + json.dumps(counts, sort_keys=True),
        "RUNNER_ENV_JSON=" + json.dumps({"python": "3.12.15"}),
        f"RUNNER_JUNIT_BYTES={len(raw) if size is None else size}",
        "RUNNER_JUNIT_SHA256=" + (sha or hashlib.sha256(raw).hexdigest()),
        "RUNNER_JUNIT_BEGIN",
        base64.b64encode(raw).decode(),
        "RUNNER_JUNIT_END",
    ]
    return ("\n".join(lines) + "\n").encode()


def make_job(tmp_path):
    repo = tmp_path / "src"
    repo.mkdir()
    (repo / "app.py").write_text("def convert(value):\n    return value * 2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(repo), "goal": "upgrade python", "request_id": "ev-1"}
    )
    return engine, job, repo


def write_output(tmp_path, name, payload):
    path = tmp_path / name
    path.write_bytes(payload)
    return str(path)


def record(engine, job, phase, output_path, source_digest=None, cases=CASES):
    return engine.invoke(
        "record",
        {
            "job": job["job_id"],
            "phase": phase,
            "expectation": expectation(cases),
            "output": output_path,
            "source_digest": source_digest or job["assessment"]["source_digest"],
        },
    )


# --- proven chain: record -> persisted -> compare -> report -----------------


def test_record_persists_and_compare_uses_paired_evaluations(tmp_path):
    engine, job, _ = make_job(tmp_path)
    baseline = record(
        engine, job, "baseline", write_output(tmp_path, "baseline.bin", output())
    )
    assert baseline["accepted"] is True and baseline["proof"] == "NOT_PROVEN"
    assert baseline["grade"] == "candidate-authored-per-case-junit"
    assert baseline["expected_count"] == 3 and baseline["results_recorded"] == 3
    candidate_digest = (
        job["assessment"]["source_digest"][:-4] + "abcd"
    )  # declared candidate tree identity differs from the baseline tree
    record(
        engine,
        job,
        "candidate",
        write_output(tmp_path, "candidate.bin", output()),
        source_digest=candidate_digest,
    )
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    assert comparison["verdict"] == "NOT_PROVEN"
    assert comparison["execution_performed"] is False
    assert comparison["compared_cases"] == 3
    inner = comparison["comparison"]
    assert inner["verdict"] == "SAME_SELECTED_SCOPE" and inner["proof"] == "NOT_PROVEN"
    assert inner["grade"] == "candidate-authored-per-case-junit"
    assert [row["verdict"] for row in inner["cases"]] == ["same"] * 3
    assert any("independent capture" in gap for gap in comparison["missing_evidence"])
    report = engine.invoke("report", {"job": job["job_id"]})
    assert json.loads(report["json"])["compared_cases"] == 3
    assert "NOT_PROVEN" in report["text"] and "NOT_PROVEN" in report["html"]


def test_compare_without_evidence_keeps_gap_only_contract(tmp_path):
    engine, job, _ = make_job(tmp_path)
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    assert comparison["compared_cases"] == 0
    assert comparison["verdict"] == "NOT_PROVEN" and comparison["missing_evidence"]
    assert "comparison" not in comparison


def test_compare_with_single_phase_names_the_absent_phase(tmp_path):
    engine, job, _ = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    assert comparison["compared_cases"] == 0
    assert any("candidate" in gap for gap in comparison["missing_evidence"])


# --- fail-closed record paths ----------------------------------------------


def test_record_refuses_mutant_output_failing_a_predeclared_case(tmp_path):
    engine, job, _ = make_job(tmp_path)
    rows = passing()
    rows[0] = (rows[0][0], rows[0][1], "<failure>changed value</failure>")
    with pytest.raises(ContractError, match="did not pass"):
        record(engine, job, "baseline",
               write_output(tmp_path, "bad.bin", output(rows)))


def test_record_refuses_forged_counts_and_missing_output(tmp_path):
    engine, job, _ = make_job(tmp_path)
    forged = output(counts={"collected": 9, "failures": 0, "errors": 0, "skipped": 0})
    with pytest.raises(ContractError):
        record(engine, job, "baseline", write_output(tmp_path, "forge.bin", forged))
    with pytest.raises(ContractError):
        record(engine, job, "baseline", str(tmp_path / "missing.bin"))
    with pytest.raises(ContractError):
        record(engine, job, "baseline", str(tmp_path))


def test_record_refuses_symlinked_output_and_duplicate_phase(tmp_path):
    engine, job, _ = make_job(tmp_path)
    real = tmp_path / "real.bin"
    real.write_bytes(output())
    link = tmp_path / "link.bin"
    link.symlink_to(real)
    with pytest.raises(ContractError):
        record(engine, job, "baseline", str(link))
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    with pytest.raises(ContractError):
        record(engine, job, "baseline", str(real))


def test_record_refuses_wrong_baseline_binding_and_stale_source(tmp_path):
    engine, job, repo = make_job(tmp_path)
    with pytest.raises(ContractError):
        record(engine, job, "baseline", write_output(tmp_path, "x.bin", output()), "a" * 64)
    digest = job["assessment"]["source_digest"]
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    (repo / "app.py").write_text("def convert(value):\n    return value * 3\n")
    with pytest.raises(ContractError):
        record(
            engine,
            job,
            "candidate",
            write_output(tmp_path, "candidate.bin", output()),
            source_digest=digest,
        )


def test_record_refuses_oversize_and_malformed_expectation(tmp_path):
    engine, job, _ = make_job(tmp_path)
    path = write_output(tmp_path, "big.bin", output())
    with pytest.raises(ContractError):
        engine.invoke(
            "record",
            {
                "job": job["job_id"],
                "phase": "baseline",
                "expectation": dict(expectation(), cases=expectation()["cases"] * 4000),
                "output": path,
                "source_digest": job["assessment"]["source_digest"],
            },
        )
    with pytest.raises(ContractError):
        engine.invoke(
            "record",
            {
                "job": job["job_id"],
                "phase": "baseline",
                "expectation": dict(expectation(), skip_policy="some"),
                "output": path,
                "source_digest": job["assessment"]["source_digest"],
            },
        )


# --- fail-closed compare paths ---------------------------------------------


def test_compare_fails_closed_on_stale_recorded_evidence(tmp_path):
    engine, job, repo = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    (repo / "note.txt").write_text("change after recording\n")
    with pytest.raises(ContractError, match="[Ss]tale"):
        engine.invoke("compare", {"job": job["job_id"]})


def test_compare_fails_closed_on_tampered_store_row(tmp_path):
    engine, job, _ = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    import sqlite3

    store = tmp_path / "private" / "jobs.sqlite"
    with sqlite3.connect(store) as connection:
        connection.execute("UPDATE evaluations SET body=? WHERE phase='baseline'", (b"{} \x00",))
    with pytest.raises(ContractError):
        engine.invoke("compare", {"job": job["job_id"]})


def test_compare_fails_closed_on_cross_expectation_pairing(tmp_path):
    engine, job, _ = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    with pytest.raises(ContractError):
        record(
            engine,
            job,
            "candidate",
            write_output(tmp_path, "candidate.bin", output()),
            cases=CASES[:2],
        )


def test_compare_with_evidence_never_launches_processes(tmp_path, monkeypatch):
    engine, job, _ = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    record(engine, job, "candidate", write_output(tmp_path, "candidate.bin", output()))
    import socket
    import subprocess
    import urllib.request

    def bomb(*args, **kwargs):
        raise AssertionError("read-only service executed code or network")

    monkeypatch.setattr(subprocess, "run", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    monkeypatch.setattr(socket, "socket", bomb)
    monkeypatch.setattr(urllib.request, "urlopen", bomb)
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    assert comparison["verdict"] == "NOT_PROVEN" and comparison["compared_cases"] == 3
    engine.invoke("report", {"job": job["job_id"]})


# --- public protocol producer surface --------------------------------------


def test_protocol_exposes_owned_producer_with_digest():
    result = Engine("/tmp").invoke("protocol", {})
    assert result["protocol"] == "junit-stdout-v1"
    assert result["producer_sha256"]
    assert result["execution_performed"] is False


# --- public CLI surface for the end user -----------------------------------


def test_cli_end_user_record_compare_report(tmp_path):
    import contextlib
    import io

    from hermes_modernisation.__main__ import main

    engine_root = tmp_path / "private"
    repo = tmp_path / "cli-src"
    repo.mkdir()
    (repo / "app.py").write_text("def convert(value):\n    return value * 2\n")

    def cli(*args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(list(args))
        assert code == 0, buffer.getvalue()
        return json.loads(buffer.getvalue())

    job = cli(
        "--data-dir", str(engine_root), "assess",
        "--repo", str(repo), "--goal", "upgrade", "--request-id", "cli-1",
    )
    recorded = cli(
        "--data-dir", str(engine_root), "record",
        "--job", job["job_id"], "--phase", "baseline",
        "--expectation", json.dumps(expectation()),
        "--output", write_output(tmp_path, "cli.bin", output()),
        "--source-digest", job["assessment"]["source_digest"],
    )
    assert recorded["accepted"] is True and recorded["proof"] == "NOT_PROVEN"
    comparison = cli("--data-dir", str(engine_root), "compare", "--job", job["job_id"])
    assert comparison["verdict"] == "NOT_PROVEN"
    assert any("candidate" in gap for gap in comparison["missing_evidence"])
    report = cli("--data-dir", str(engine_root), "report", "--job", job["job_id"])
    assert "NOT_PROVEN" in report["text"]


def test_run_resume_approve_still_refuse(tmp_path):
    engine, job, _ = make_job(tmp_path)
    for action in ("run", "resume", "approve"):
        with pytest.raises(ContractError):
            engine.invoke(action, {"job": job["job_id"]})


# --- round-2 corrections (implementer-owned; distinct from the immutable ----
# --- controller regression file in test_review_regressions.py) --------------


def test_record_refuses_candidate_paired_to_reordered_expectation_at_write(tmp_path):
    """A reordered (same-set) expectation has a different digest but a genuinely
    accepted output, so the pairing mismatch must be refused at WRITE time."""
    engine, job, _ = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    reordered = [list(case) for case in reversed(CASES)]
    with pytest.raises(ContractError, match="different expectation"):
        record(
            engine,
            job,
            "candidate",
            write_output(tmp_path, "cand.bin", output()),
            cases=reordered,
        )
    rows = engine.store.evidence_for(job["job_id"])
    assert [row["phase"] for row in rows] == ["baseline"]


def test_store_refuses_non_object_evaluation_body_at_write(tmp_path):
    engine, job, _ = make_job(tmp_path)
    from hermes_modernisation.evaluator import load_expectation
    from hermes_modernisation.jsonio import dumps

    valid = load_expectation(dumps(expectation()))
    with pytest.raises(ContractError, match="must be a JSON object"):
        engine.store.record_evaluation(
            job["job_id"],
            "baseline",
            job["assessment"]["source_digest"],
            valid,
            "not-an-object",
        )
    assert engine.store.evidence_for(job["job_id"]) == []


def test_compare_fails_closed_on_sha_consistent_non_object_body(tmp_path):
    """A valid hash over a non-object body must still fail closed explicitly."""
    engine, job, _ = make_job(tmp_path)
    record(engine, job, "baseline", write_output(tmp_path, "baseline.bin", output()))
    import sqlite3

    payload = json.dumps(["unexpected", "non-object"]).encode()
    with sqlite3.connect(tmp_path / "private" / "jobs.sqlite") as connection:
        connection.execute(
            "UPDATE evaluations SET body=?, body_sha256=? WHERE phase='baseline'",
            (payload, hashlib.sha256(payload).hexdigest()),
        )
    with pytest.raises(ContractError, match="corrupted"):
        engine.invoke("compare", {"job": job["job_id"]})


def test_cli_refuses_deeply_nested_expectation_json(tmp_path):
    import contextlib
    import io

    from hermes_modernisation.__main__ import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(
            [
                "--data-dir",
                str(tmp_path / "private"),
                "status",
                "--expectation",
                "[" * 60000,
            ]
        )
    assert code == 2
    assert "INVALID_ARGUMENTS" in buffer.getvalue()


def test_tool_adapter_refuses_deeply_nested_expectation_json():
    from hermes_modernisation.adapters.hermes import arguments_for

    with pytest.raises(ContractError):
        arguments_for({"expectation": "[" * 60000})
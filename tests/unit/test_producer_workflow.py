"""Real producer/consumer chain, witnessed end to end inside the approved
development sandbox: the owned junit-stdout-v1 producer program runs pytest on
a tiny fixture application, and the captured retained output is recorded
through the public engine record action, then compared by compare/report.

Boundary: fixture authority only. No real walkie execution happens here, no
network is used, and fixture values are synthetic. Capture happens inside the
environment that runs the tests (candidate-authored per-case JUnit), so the
transport-independence limitation stays explicitly OPEN; nothing here upgrades
recorded evidence to proof.
"""

import subprocess
import sys

import pytest

from hermes_modernisation.jsonio import ContractError
from hermes_modernisation.runner import PROGRAM
from hermes_modernisation.service import Engine

APP = '''"""Fixture application (synthetic values; no real credentials)."""

AUTH_TOKEN = "fixture-ok"
AUDIT = []


def convert(value):
    return value * 2


def authenticate(token):
    return token == AUTH_TOKEN


def record_event(event):
    AUDIT.append(event)
    return len(AUDIT)
'''

TESTS = '''from app import AUDIT, authenticate, convert, record_event


def test_convert():
    assert convert(2) == 4


def test_authenticate_accepts_and_refuses():
    assert authenticate("fixture-ok") is True
    assert authenticate("nope") is False


def test_record_event_records_and_counts():
    AUDIT.clear()
    assert record_event("open") == 1
    assert AUDIT == ["open"]
'''

EXPECTATION = {
    "schema_version": 1,
    "kind": "junit-per-case",
    "skip_policy": "none",
    "cases": [
        ["test_app", "test_convert"],
        ["test_app", "test_authenticate_accepts_and_refuses"],
        ["test_app", "test_record_event_records_and_counts"],
    ],
}


def run_chain(tmp_path, app_text, name):
    project = tmp_path / (name + "-fixture")
    project.mkdir()
    (project / "app.py").write_text(app_text)
    (project / "test_app.py").write_text(TESTS)
    producer = tmp_path / name
    producer.write_text(PROGRAM)
    proc = subprocess.run(
        [sys.executable, "-B", str(producer), "test_app.py"],
        cwd=str(project),
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout[-400:] + proc.stderr[-400:]
    return project, proc.stdout


def make_job(tmp_path, repo=None):
    repo = repo or tmp_path / "job-src"
    repo.mkdir()
    (repo / "app.py").write_text("def convert(value):\n    return value * 2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(repo), "goal": "upgrade", "request_id": "chain"}
    )
    return engine, job


def record(engine, job, phase, stdout):
    retained = tmp_store(job)
    path = retained / (phase + ".bin")
    path.write_bytes(stdout)
    return engine.invoke(
        "record",
        {
            "job": job["job_id"],
            "phase": phase,
            "expectation": EXPECTATION,
            "output": str(path),
            "source_digest": job["assessment"]["source_digest"],
        },
    )


def tmp_store(job):
    from pathlib import Path

    path = Path(job["repo"]).parent / "retained"
    path.mkdir(exist_ok=True)
    return path


def test_producer_chain_records_accepted_run_and_compares(tmp_path):
    engine, job = make_job(tmp_path)
    project, captured = run_chain(tmp_path, APP, "producer-baseline")
    assert b"RUNNER_JUNIT_BEGIN" in captured
    baseline = record(engine, job, "baseline", captured)
    assert baseline["accepted"] is True and baseline["proof"] == "NOT_PROVEN"
    assert baseline["expected_count"] == 3
    _, candidate = run_chain(tmp_path, APP, "producer-candidate")
    record(engine, job, "candidate", candidate)
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    assert comparison["comparison"]["verdict"] == "SAME_SELECTED_SCOPE"
    assert comparison["verdict"] == "NOT_PROVEN"
    assert comparison["compared_cases"] == 3


def test_changed_value_mutant_is_refused(tmp_path):
    engine, job = make_job(tmp_path)
    _, captured = run_chain(tmp_path, APP.replace("value * 2", "value * 3"), "mutant-value")
    with pytest.raises(ContractError, match="did not pass"):
        record(engine, job, "baseline", captured)


def test_wrong_auth_mutant_is_refused(tmp_path):
    engine, job = make_job(tmp_path)
    _, captured = run_chain(
        tmp_path, APP.replace('"fixture-ok"', '"mutant-token"'), "mutant-auth"
    )
    with pytest.raises(ContractError, match="did not pass"):
        record(engine, job, "baseline", captured)


def test_missing_side_effect_mutant_is_refused(tmp_path):
    engine, job = make_job(tmp_path)
    _, captured = run_chain(
        tmp_path, APP.replace("AUDIT.append(event)", "pass"), "mutant-side-effect"
    )
    with pytest.raises(ContractError, match="did not pass"):
        record(engine, job, "baseline", captured)


def test_erroring_mutant_is_refused(tmp_path):
    engine, job = make_job(tmp_path)
    mutating = APP.replace(
        "    return value * 2", "    raise RuntimeError('mutant')"
    )
    _, captured = run_chain(tmp_path, mutating, "mutant-error")
    with pytest.raises(ContractError, match="did not pass"):
        record(engine, job, "baseline", captured)


def test_forged_count_declaration_is_refused_before_storage(tmp_path):
    engine, job = make_job(tmp_path)
    _, captured = run_chain(tmp_path, APP, "producer-forge")
    forged = captured.replace(b'"collected": 3', b'"collected": 9', 1)
    assert forged != captured
    with pytest.raises(ContractError, match="re-derivation"):
        record(engine, job, "baseline", forged)
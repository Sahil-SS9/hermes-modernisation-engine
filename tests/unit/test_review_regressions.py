"""Controller-owned public-boundary regressions; RED before remediation.

Run only through the approved isolated development gate. All stores, sources,
FIFOs and child processes are disposable fixtures, never operator state.
"""

import json
import os
import sqlite3
import subprocess
import sys

import pytest

from hermes_modernisation.jsonio import ContractError
from hermes_modernisation.service import Engine
from test_metadata_recipe import apply as apply_recipe
from test_metadata_recipe import make_source as make_recipe_source


def make_job(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("def double(value):\n    return value * 2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(source), "goal": "upgrade", "request_id": "review"}
    )
    return engine, job


@pytest.mark.parametrize("version", [1, 2])
def test_legacy_compare_and_report_remain_read_only_without_migration(tmp_path, version):
    engine, job = make_job(tmp_path)
    database = tmp_path / "private" / "jobs.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE evaluations")
        if version == 1:
            connection.execute("DROP TABLE details")
        connection.execute(f"PRAGMA user_version={version}")
    before = database.read_bytes()
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    report = engine.invoke("report", {"job": job["job_id"]})
    assert comparison["compared_cases"] == 0
    assert comparison["verdict"] == "NOT_PROVEN"
    assert report["text"].startswith("NOT_PROVEN")
    assert database.read_bytes() == before
    assert not (tmp_path / "private" / "jobs.pre-v3.sqlite").exists()


def test_record_refuses_fifo_without_waiting_for_a_writer(tmp_path):
    engine, job = make_job(tmp_path)
    output = tmp_path / "output.fifo"
    os.mkfifo(output)
    arguments = {
        "job": job["job_id"],
        "phase": "baseline",
        "expectation": {
            "schema_version": 1,
            "kind": "junit-per-case",
            "skip_policy": "none",
            "cases": [["test_app", "test_double"]],
        },
        "output": str(output),
        "source_digest": job["assessment"]["source_digest"],
    }
    child = (
        "import json,sys\n"
        "from hermes_modernisation.service import Engine\n"
        "from hermes_modernisation.jsonio import ContractError\n"
        "try:\n"
        "    Engine(sys.argv[1]).invoke('record', json.loads(sys.argv[2]))\n"
        "except ContractError:\n"
        "    print('FIFO_REFUSED')\n"
        "else:\n"
        "    raise SystemExit('unsafe FIFO accepted')\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-c", child, str(engine.store.root), json.dumps(arguments)],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("record hung while opening a FIFO before validating its file type")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "FIFO_REFUSED"
    assert engine.store.evidence_for(job["job_id"]) == []


def test_recipe_refuses_matching_preimage_hidden_in_a_comment(tmp_path):
    source = make_recipe_source(tmp_path)
    metadata = source / "pyproject.toml"
    original = metadata.read_text()
    metadata.write_text(
        original.replace(
            'dashboard = ["fastapi==0.115.6"]',
            'dashboard = ["fastapi==0.120.0"]\n# dashboard = ["fastapi==0.115.6"]',
        )
    )
    destination = tmp_path / "candidate"
    with pytest.raises(ContractError):
        apply_recipe(Engine(tmp_path / "private"), source, destination)
    assert not destination.exists()

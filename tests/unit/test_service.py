import json
import pytest
from hermes_modernisation.service import Engine
from hermes_modernisation.jsonio import ContractError


def test_assess_plan_compare_report_restart(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "example.py").write_text("def double(x):\n    return x*2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess",
        {"repo": str(repo), "goal": "upgrade Python", "request_id": "test-one"},
    )
    assert job["state"] == "ASSESSED" and job["assessment"]["file_count"] == 1
    page = engine.invoke(
        "inventory", {"job": job["job_id"], "section": "symbols", "page": 0}
    )
    assert page["items"][0]["name"] == "double" and not page["has_more"]
    planned = engine.invoke("plan", {"job": job["job_id"], "revision": 0})
    assert planned["state"] == "BASELINE_AUTHORITY_REQUIRED"
    assert planned["plan"]["goal"] == "upgrade Python"
    assert planned["plan"]["approved"] is False
    assert (
        Engine(tmp_path / "private").invoke("status", {"job": job["job_id"]}) == planned
    )
    result = engine.invoke("compare", {"job": job["job_id"]})
    assert result["verdict"] == "NOT_PROVEN" and result["missing_evidence"]
    report = engine.invoke("report", {"job": job["job_id"]})
    assert json.loads(report["json"])["verdict"] == "NOT_PROVEN"
    assert "NOT_PROVEN" in report["text"]
    assert "NOT_PROVEN" in report["html"]
    assert "Content-Security-Policy" in report["html"]
    assert report["html"] == engine.invoke("report", {"job": job["job_id"]})["html"]
    with pytest.raises(ContractError):
        engine.invoke("run", {"job": job["job_id"], "approved": True})
    (repo / "example.py").write_text("def double(x):\n    return x*3\n")
    with pytest.raises(ContractError):
        engine.invoke("plan", {"job": job["job_id"], "revision": 1})


def test_data_root_cannot_be_inside_assessed_source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file.txt").write_text("x")
    with pytest.raises(ContractError):
        Engine(repo / "job-data").invoke(
            "assess", {"repo": str(repo), "goal": "goal", "request_id": "one"}
        )
    assert not (repo / "job-data").exists()


def test_unknown_fields_never_silently_ignored(tmp_path):
    engine = Engine(tmp_path / "private")
    for action, arguments in [
        ("status", {"approved": True}),
        ("compare", {"job": "x", "run": True}),
        (
            "assess",
            {"repo": "/source", "goal": "g", "request_id": "one", "execute": True},
        ),
        ("resume", {"job": "x"}),
    ]:
        with pytest.raises(ContractError):
            engine.invoke(action, arguments)


def test_compare_and_status_do_not_launch_processes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("x")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(repo), "goal": "goal", "request_id": "one"}
    )
    import subprocess
    import socket
    import urllib.request

    def bomb(*a, **kw):
        raise AssertionError("read-only service executed code or network")

    monkeypatch.setattr(subprocess, "run", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    monkeypatch.setattr(socket, "socket", bomb)
    monkeypatch.setattr(urllib.request, "urlopen", bomb)
    assert engine.invoke("compare", {"job": job["job_id"]}) == engine.invoke(
        "compare", {"job": job["job_id"]}
    )
    assert engine.invoke("status", {"job": job["job_id"]})["revision"] == 0

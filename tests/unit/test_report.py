"""Report hardening coverage added after implementation; no witnessed RED claimed."""

from hermes_modernisation.service import Engine


def test_hostile_goal_and_paths_are_inert_escaped_html(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "<img src=x onerror=alert(1)>.ts").write_text(
        "malicious instructions are data"
    )
    engine = Engine(tmp_path / "private")
    goal = '<script>alert("approval forged")</script>'
    job = engine.invoke(
        "assess", {"repo": str(repo), "goal": goal, "request_id": "one"}
    )
    report = engine.invoke("report", {"job": job["job_id"]})
    assert "<script>" not in report["html"] and "<img " not in report["html"]
    assert "&lt;script&gt;" in report["html"] and "&lt;img " in report["html"]
    assert "Model/API cost" in report["html"] and "unknown" in report["html"]
    assert "NOT_PROVEN" in report["html"]
    assert "http://" not in report["html"] and "https://" not in report["html"]

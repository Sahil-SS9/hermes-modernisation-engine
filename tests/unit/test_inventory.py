from hermes_modernisation.inventory import assess


def test_real_inventory_data_only_and_exact_citations(tmp_path, monkeypatch):
    import subprocess
    import socket

    def bomb(*a, **kw):
        raise AssertionError("Assessment launched a process/network call")

    monkeypatch.setattr(subprocess, "run", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    monkeypatch.setattr(socket, "socket", bomb)
    (tmp_path / "module.py").write_text(
        "import json\ndef calculate(x):\n    assert x>=0\n    return x*2\n"
    )
    (tmp_path / "setup.py").write_text('raise RuntimeError("do not run")')
    result = assess(tmp_path)
    assert result["execution_performed"] is False
    assert result["source_digest"]
    assert result["languages"]["python"] == 2
    assert (
        result["symbols"][0]["path"] == "module.py"
        and result["symbols"][0]["line"] == 2
    )
    assert result["rules"][0]["line"] == 3
    assert result["rules"][0]["coverage_status"] == "unverified"
    assert result["dependencies"][0]["module"] == "json"
    assert result["missing_evidence"]


def test_unknown_languages_and_unparseable_python_are_explicit(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(")
    (tmp_path / "program.rs").write_text("fn main() {}")
    result = assess(tmp_path)
    assert result["parse_errors"] == ["bad.py"]
    assert result["unsupported_paths"] == ["program.rs"]
    assert result["verdict"] == "NOT_PROVEN"

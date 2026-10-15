import os
import pytest
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError


def test_snapshot_binds_ignored_source_config_and_modes(tmp_path):
    (tmp_path / "a.py").write_text("print(1)")
    first = snapshot(tmp_path)
    assert first["complete"] and first["file_count"] == 1
    (tmp_path / "ignored.txt").write_text("relevant")
    second = snapshot(tmp_path)
    assert first["digest"] != second["digest"]
    (tmp_path / "a.py").chmod(0o755)
    assert snapshot(tmp_path)["digest"] != second["digest"]
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git-private")
    assert ".git/config" not in [f["path"] for f in snapshot(tmp_path)["files"]]


def test_snapshot_refuses_links_secret_files_and_special_files(tmp_path):
    (tmp_path / "target").write_text("x")
    link = tmp_path / "alias"
    link.symlink_to("target")
    with pytest.raises(ContractError):
        snapshot(tmp_path)
    link.unlink()
    os.link(tmp_path / "target", link)
    with pytest.raises(ContractError):
        snapshot(tmp_path)
    link.unlink()
    (tmp_path / ".env").write_text("SECRET=never-export")
    with pytest.raises(ContractError):
        snapshot(tmp_path)
    (tmp_path / ".env").unlink()
    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(ContractError):
        snapshot(tmp_path)


def test_no_execution_and_deterministic(tmp_path, monkeypatch):
    import socket
    import subprocess

    def bomb(*args, **kwargs):
        raise AssertionError("Execution during inventory")

    monkeypatch.setattr(subprocess, "run", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    monkeypatch.setattr(socket, "socket", bomb)
    (tmp_path / "setup.py").write_text('raise RuntimeError("DO NOT RUN")')
    assert snapshot(tmp_path) == snapshot(tmp_path)


def test_directory_symlink_and_ambiguous_root_refused(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (tmp_path / "alias").symlink_to(root, target_is_directory=True)
    with pytest.raises(ContractError):
        snapshot(tmp_path / "alias")
    (root / "outside").symlink_to("/tmp", target_is_directory=True)
    with pytest.raises(ContractError):
        snapshot(root)

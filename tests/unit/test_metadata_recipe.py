"""Fixed-recipe (NO AI) metadata upgrade behaviour through the public engine
surface: a reviewed engine-owned recipe prepares exact metadata edits in a
fresh disposable candidate root, with strict preimage/base validation, failed
residue preserved, no execution/lockfile/installation, and a usable diff.

The known-good walkie-trial candidate (mounted read-only at /benchmark in the
approved container, when present) is used as a comparison oracle for target
literals and declared remaining differences — never executed.
"""

from pathlib import Path

import json
import pytest

from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError
from hermes_modernisation.service import Engine

RECIPE_ID = "python314-fastapi-metadata-v1"

FIXTURE_PYPROJECT = """[build-system]
requires = ["setuptools==83.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "fixture-app"
version = "0.1.0"
requires-python = ">=3.11,<3.14"
authors = [{ name = "Fixture" }]
classifiers = [
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Communications",
]
dependencies = []

[project.optional-dependencies]
dashboard = ["fastapi==0.115.6"]

[dependency-groups]
dev = [
    "fastapi==0.115.6",
    "httpx==0.27.2",
    "pytest-asyncio==0.24.0",
]
"""

FIXTURE_CI = """name: tests
on: [push]
jobs:
  test:
    strategy:
      matrix:
        # POSIX suite
        os: [ubuntu-latest]
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - run: echo fixture only
"""

FIXTURE_APP = "def convert(value):\n    return value * 2\n"

TARGET_LINES = (  # recorded from the owner-approved v3/v4 trial result
    'requires-python = ">=3.11,<3.15"',
    '"Programming Language :: Python :: 3.14"',
    'dashboard = ["fastapi==0.133.1"]',
    '"httpx==0.28.1"',
)
CI_TARGET = 'python-version: ["3.11", "3.12", "3.13", "3.14"]'
CI_PREIMAGE = 'python-version: ["3.11", "3.12", "3.13"]'


def make_source(tmp_path):
    source = tmp_path / "source"
    (source / ".github" / "workflows").mkdir(parents=True)
    (source / "pyproject.toml").write_text(FIXTURE_PYPROJECT)
    (source / ".github" / "workflows" / "ci.yml").write_text(FIXTURE_CI)
    (source / "app.py").write_text(FIXTURE_APP)
    return source


def apply(engine, source, destination, recipe=RECIPE_ID, **overrides):
    arguments = {
        "repo": str(source),
        "recipe": recipe,
        "base_digest": snapshot(source)["digest"],
        "dest": str(destination),
    }
    arguments.update(overrides)
    return engine.invoke("recipe", arguments)


def make_engine(tmp_path):
    return Engine(tmp_path / "private")


def test_recipe_builds_disposable_candidate_from_original_metadata(tmp_path):
    source = make_source(tmp_path)
    before = snapshot(source)
    result = apply(make_engine(tmp_path), source, tmp_path / "candidate")
    assert result["changed_paths"] == [".github/workflows/ci.yml", "pyproject.toml"]
    assert result["approved"] is False
    assert result["execution_performed"] is False
    assert result["install_performed"] is False
    assert result["verdict"] == "NOT_PROVEN"
    candidate = Path(result["candidate_root"])
    metadata = (candidate / "pyproject.toml").read_text()
    for line in TARGET_LINES:
        assert line in metadata, line
    assert (candidate / ".github/workflows/ci.yml").read_text().count(CI_TARGET) == 1
    assert (candidate / "app.py").read_text() == FIXTURE_APP
    assert result["source_digest"] == before["digest"]
    assert result["candidate_digest"] == snapshot(candidate)["digest"]
    assert (candidate / "pyproject.toml").read_bytes() != (source / "pyproject.toml").read_bytes()
    # Original source is retained unchanged.
    assert snapshot(source)["digest"] == before["digest"]
    assert 'requires-python = ">=3.11,<3.14"' in (source / "pyproject.toml").read_text()
    assert 'requires-python = ">=3.11,<3.15"' in metadata
    # Usable diff for review.
    diff = result["diff"]["pyproject.toml"]
    assert "-requires-python = \">=3.11,<3.14\"" in diff
    assert '+requires-python = ">=3.11,<3.15"' in diff
    assert "+    \"Programming Language :: Python :: 3.14\"," in diff
    assert "-    \"fastapi==0.115.6\"," in diff and '+    "fastapi==0.133.1",' in diff
    assert len(diff) <= 20000
    # Non-contract edits are part of the recipe, not the caller.
    assert any(refusal["path"] == "uv.lock" for refusal in result["declared_refusals"])


def test_recipe_refuses_unknown_recipe_stale_base_and_occupied_destination(tmp_path):
    source = make_source(tmp_path)
    engine = make_engine(tmp_path)
    with pytest.raises(ContractError):
        apply(engine, source, tmp_path / "c1", recipe="python314-everything-v9")
    with pytest.raises(ContractError, match="[Ss]tale"):
        engine.invoke(
            "recipe",
            {
                "repo": str(source),
                "recipe": RECIPE_ID,
                "base_digest": "a" * 64,
                "dest": str(tmp_path / "c2"),
            },
        )
    with pytest.raises(ContractError):
        engine.invoke(
            "recipe",
            {
                "repo": str(source),
                "recipe": RECIPE_ID,
                "base_digest": snapshot(source)["digest"],
                "dest": str(tmp_path / "c3"),
                "extra": "out-of-contract field",
            },
        )
    (tmp_path / "c4").mkdir()
    with pytest.raises(ContractError):
        apply(engine, source, tmp_path / "c4")
    with pytest.raises(ContractError):
        apply(engine, source, source / "nested")


def test_cli_recipe_surface_reports_usable_diff(tmp_path):
    import contextlib
    import io

    from hermes_modernisation.__main__ import main

    source = make_source(tmp_path)

    def cli(*args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(list(args))
        assert code == 0, buffer.getvalue()
        return json.loads(buffer.getvalue())

    result = cli(
        "--data-dir", str(tmp_path / "private"), "recipe",
        "--repo", str(source), "--recipe", RECIPE_ID,
        "--base-digest", snapshot(source)["digest"],
        "--dest", str(tmp_path / "candidate"),
    )
    assert result["changed_paths"] == [".github/workflows/ci.yml", "pyproject.toml"]
    assert 'requires-python = ">=3.11,<3.15"' in result["diff"]["pyproject.toml"]
    assert result["declared_refusals"][0]["path"] == "uv.lock"


def test_recipe_preserves_failed_residue_and_refuses_reuse(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    expected_digest = snapshot(source)["digest"]
    import hermes_modernisation.recipes as recipes

    real_read = recipes.read_source
    seen = []

    def flaky(root, relative):
        if relative == "app.py" and seen:
            # fail mid-copy after the first file was already materialised
            raise OSError("simulated copy failure")
        seen.append(relative)
        return real_read(root, relative)

    monkeypatch.setattr(recipes, "read_source", flaky)
    destination = tmp_path / "candidate"
    engine = make_engine(tmp_path)
    with pytest.raises(ContractError):
        engine.invoke(
            "recipe",
            {
                "repo": str(source),
                "recipe": RECIPE_ID,
                "base_digest": expected_digest,
                "dest": str(destination),
            },
        )
    monkeypatch.undo()
    assert destination.is_dir(), "failed residue must be preserved"
    residue = destination / "residue.json"
    assert residue.is_file()
    assert b"failed-residue" in residue.read_bytes()
    with pytest.raises(ContractError, match="occupied"):
        apply(engine, source, destination)


def test_recipe_never_executes_shells_or_network(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    import socket
    import subprocess
    import urllib.request

    def bomb(*args, **kwargs):
        raise AssertionError("recipe applied with process/network execution")

    monkeypatch.setattr(subprocess, "run", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    monkeypatch.setattr(socket, "socket", bomb)
    monkeypatch.setattr(urllib.request, "urlopen", bomb)
    result = apply(make_engine(tmp_path), source, tmp_path / "candidate")
    assert result["changed_paths"]


def test_recipe_refuses_non_preimage_and_symlinked_source_files(tmp_path):
    source = make_source(tmp_path)
    engine = make_engine(tmp_path)
    (source / "pyproject.toml").write_text(
        FIXTURE_PYPROJECT.replace("0.115.6", "0.116.0")
    )
    with pytest.raises(ContractError, match="[Pp]reimage"):
        apply(engine, source, tmp_path / "candidate")
    pristine = make_source(tmp_path / "linked")
    (pristine / "linked-file").symlink_to(pristine / "app.py")
    with pytest.raises(ContractError):
        apply(engine, pristine, tmp_path / "candidate-2")
    assert not (tmp_path / "candidate-2").exists()


def test_recipe_cross_checks_known_walkie_metadata_without_execution(tmp_path):
    benchmark = Path("/benchmark")
    pyproject = benchmark / "pyproject.toml"
    if not pyproject.is_file():
        pytest.skip("/benchmark not mounted (host environment)")
    engine = make_engine(tmp_path)
    # Every declared target literal matches the known-good trial candidate metadata.
    real_pyproject = pyproject.read_text()
    for line in TARGET_LINES:
        assert line in real_pyproject, line
    assert CI_TARGET in (benchmark / ".github/workflows/ci.yml").read_text()
    # Known remaining differences beyond this recipe's scope (recorded from v4):
    assert "pytest-asyncio==1.4.0" in real_pyproject
    lock = benchmark / "uv.lock"
    if lock.is_file():
        rows = lock.read_text()
        block = rows.index('[[package]]\nname = "starlette"')
        assert "0.52.1" in rows[block : block + 80]  # starlette lock row via v4 lane
    # An already-upgraded tree is refused on preimage, creating nothing.
    destination = tmp_path / "bench-candidate"
    with pytest.raises(ContractError):
        engine.invoke(
            "recipe",
            {
                "repo": str(benchmark),
                "recipe": RECIPE_ID,
                "base_digest": snapshot(benchmark)["digest"],
                "dest": str(destination),
            },
        )
    assert not destination.exists()


# --- round-2 corrections (implementer-owned) ---------------------------------


def test_recipe_refuses_ci_matrix_preimage_hidden_in_a_comment(tmp_path):
    source = make_source(tmp_path)
    workflow = source / ".github" / "workflows" / "ci.yml"
    original = workflow.read_text()
    workflow.write_text(
        original.replace(
            CI_PREIMAGE,
            'python-version: ["3.11", "3.12", "3.13", "3.12-old"]\n'
            "        # " + CI_PREIMAGE,
        )
    )
    destination = tmp_path / "candidate-comment"
    with pytest.raises(ContractError):
        apply(make_engine(tmp_path), source, destination)
    assert not destination.exists()


def test_recipe_refuses_unparseable_or_duplicate_toml_metadata(tmp_path):
    engine = make_engine(tmp_path)
    broken = make_source(tmp_path / "broken")
    (broken / "pyproject.toml").write_text(
        FIXTURE_PYPROJECT + "\ndefinitely = = broken = not toml\n"
    )
    with pytest.raises(ContractError, match="[Tt]oml"):
        apply(engine, broken, tmp_path / "candidate-broken")
    assert not (tmp_path / "candidate-broken").exists()
    duplicated = make_source(tmp_path / "duplicated")
    (duplicated / "pyproject.toml").write_text(
        FIXTURE_PYPROJECT + '\n[project]\ndescription = "duplicate declaration"\n'
    )
    with pytest.raises(ContractError, match="[Tt]oml"):
        apply(engine, duplicated, tmp_path / "candidate-duplicate")
    assert not (tmp_path / "candidate-duplicate").exists()


def test_recipe_records_residue_on_post_copy_reconciliation_failure(
    tmp_path, monkeypatch
):
    source = make_source(tmp_path)
    import hermes_modernisation.recipes as recipes

    real_snapshot = recipes.snapshot
    seen_source = []

    def flaky(root):
        result = real_snapshot(root)
        if root == source and seen_source:
            # second source-snapshot call = the post-copy reconciliation pass
            raise ContractError("Simulated post-copy reconciliation failure")
        seen_source.append(root)
        return result

    monkeypatch.setattr(recipes, "snapshot", flaky)
    destination = tmp_path / "candidate"
    engine = make_engine(tmp_path)
    with pytest.raises(ContractError, match="[Rr]econciliation"):
        apply(engine, source, destination)
    monkeypatch.undo()
    assert destination.is_dir(), "failed residue must be preserved"
    residue = destination / "residue.json"
    assert residue.is_file()
    assert b"failed-residue" in residue.read_bytes()
    with pytest.raises(ContractError, match="occupied"):
        apply(engine, source, destination)
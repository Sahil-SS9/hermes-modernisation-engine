"""uv.lock replay lane (NO resolution, NO network): the engine ingests the
owner-REVIEWED, already-tested v4 upgraded lockfile bytes as a hash-bound,
provenance-carrying DATA artifact and applies them as a byte-exact
replacement inside the fixed recipe, gated by a digest-based preimage.

The lane REPLAYS one reviewed result; it never resolves dependencies. The
known-good walkie candidate (mounted read-only at /benchmark when present)
is the byte-identity oracle: applying the extended recipe to pristine
baseline bytes must reproduce the candidate's uv.lock/pyproject/CI exactly
and leave zero declared metadata differences.
"""

import os
import threading
from pathlib import Path

import pytest

import hermes_modernisation.recipes as recipes
from hermes_modernisation.jsonio import ContractError
from test_metadata_recipe import (
    CI_PREIMAGE,
    CI_TARGET,
    FIXTURE_APP,
    FIXTURE_CI,
    FIXTURE_PYPROJECT,
    apply,
    make_engine,
)

BASE = Path(__file__).parent / "data" / "baseline"
BASELINE_LOCK = BASE / "uv.lock"
BASELINE_PYPROJECT = BASE / "pyproject.toml"
BASELINE_CI = BASE / ".github-workflows-ci.yml"

# Review-captured digests (recorded when the bytes were captured read-only
# from the benchmark clone's git history).
BASELINE_LOCK_SHA256 = "a28285e4787ac1a478a3fc1942b55b4c631678c201566276a3b73d23154b2396"
ARTIFACT_SHA256 = "a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25"


def bundle_bytes():
    """REAL upgraded lock bytes as currently bundled with the engine."""
    data = Path(recipes.__file__).resolve().with_name("data")
    return (data / "uv.lock.v4-replay").read_bytes()


def make_lock_source(tmp_path):
    """Tree satisfying the reviewed metadata preimages, with the REAL
    captured baseline uv.lock: only the lock lane behaviour varies."""
    source = tmp_path / "source"
    (source / ".github" / "workflows").mkdir(parents=True)
    (source / "pyproject.toml").write_text(FIXTURE_PYPROJECT)
    (source / ".github" / "workflows" / "ci.yml").write_text(FIXTURE_CI)
    (source / "uv.lock").write_bytes(BASELINE_LOCK.read_bytes())
    (source / "app.py").write_text(FIXTURE_APP)
    return source


def make_real_baseline(tmp_path):
    """Pristine REAL baseline tree: captured pyproject/CI/uv.lock bytes."""
    source = tmp_path / "real-baseline"
    (source / ".github" / "workflows").mkdir(parents=True)
    (source / "pyproject.toml").write_bytes(BASELINE_PYPROJECT.read_bytes())
    (source / ".github" / "workflows" / "ci.yml").write_bytes(BASELINE_CI.read_bytes())
    (source / "uv.lock").write_bytes(BASELINE_LOCK.read_bytes())
    (source / "app.py").write_text(FIXTURE_APP)
    return source


def expect_refusal(engine, source, destination, match=None):
    with pytest.raises(ContractError, match=match):
        apply(engine, source, destination)
    assert not destination.exists(), "refusal must happen before materialisation"


def test_lock_lane_replays_reviewed_artifact_byte_exact(tmp_path):
    source = make_lock_source(tmp_path)
    engine = make_engine(tmp_path)
    result = apply(engine, source, tmp_path / "candidate")
    candidate = Path(result["candidate_root"])
    assert "uv.lock" in result["changed_paths"]
    assert (candidate / "uv.lock").read_bytes() == bundle_bytes()
    lane = result["lock_lane"]
    assert lane["kind"] == "reviewed-artifact-replay"
    assert lane["replays"] and "v4" in lane["replays"]
    assert lane["baseline_sha256"] == BASELINE_LOCK_SHA256
    assert lane["artifact_sha256"] == ARTIFACT_SHA256
    assert lane["performs_dependency_resolution"] is False
    delta = lane["package_delta"]
    assert delta["changed"] == {
        "fastapi": ["0.115.6", "0.133.1"],
        "httpx": ["0.27.2", "0.28.1"],
        "pytest-asyncio": ["0.24.0", "1.4.0"],
        "starlette": ["0.41.3", "0.52.1"],
    }
    assert delta["added"] == {"annotated-doc": "0.0.5"}
    assert delta["removed"] == {"sniffio": "1.3.1"}
    assert result["resolution_performed"] is False
    assert result["execution_performed"] is False


def test_lock_lane_refuses_drifted_lock_bytes(tmp_path):
    source = make_lock_source(tmp_path)
    lock = source / "uv.lock"
    drifted = lock.read_bytes() + b"\n# someone resolved something\n"
    lock.write_bytes(drifted)
    expect_refusal(make_engine(tmp_path), source, tmp_path / "candidate", match="preimage")


def test_lock_lane_refuses_absent_lock(tmp_path):
    source = make_lock_source(tmp_path)
    (source / "uv.lock").unlink()
    expect_refusal(make_engine(tmp_path), source, tmp_path / "candidate")


def test_lock_lane_refuses_completed_already(tmp_path):
    source = make_lock_source(tmp_path)
    (source / "uv.lock").write_bytes(bundle_bytes())
    expect_refusal(make_engine(tmp_path), source, tmp_path / "candidate", match="already")


def test_lock_artifact_tamper_refused_before_materialisation(tmp_path, monkeypatch):
    tamper_dir = tmp_path / "tampered-data" / "data"
    tamper_dir.mkdir(parents=True)
    tampered = bundle_bytes().replace(b"pytest-asyncio", b"pytest-dismantl", 1)
    (tamper_dir / "uv.lock.v4-replay").write_bytes(tampered)
    # The loader derives its bundle directory from the recipes module's
    # __file__; pointing that at the tampered copy exercises the real
    # hash-pinned check against modified bytes.
    monkeypatch.setattr(recipes, "__file__", str(tamper_dir.parent / "recipes.py"))
    expect_refusal(
        make_engine(tmp_path), make_lock_source(tmp_path), tmp_path / "candidate",
        match="tamper",
    )


def test_dev_pin_bump_joins_parsed_fields(tmp_path):
    source = make_lock_source(tmp_path)
    candidate = Path(
        apply(make_engine(tmp_path), source, tmp_path / "candidate")["candidate_root"]
    )
    metadata = (candidate / "pyproject.toml").read_text()
    assert '"pytest-asyncio==1.4.0",' in metadata
    assert '"pytest-asyncio==0.24.0",' not in metadata


def test_dev_pin_preimage_refused_when_pin_absent(tmp_path):
    source = make_lock_source(tmp_path)
    metadata = source / "pyproject.toml"
    metadata.write_text(
        metadata.read_text().replace('    "pytest-asyncio==0.24.0",\n', "")
    )
    expect_refusal(make_engine(tmp_path), source, tmp_path / "candidate", match="[Pp]reimage")


def test_dev_pin_token_in_comment_refused(tmp_path):
    source = make_lock_source(tmp_path)
    metadata = source / "pyproject.toml"
    original = metadata.read_text()
    metadata.write_text(
        original.replace(
            '    "pytest-asyncio==0.24.0",\n',
            '    "pytest-asyncio==0.30.0",\n    # "pytest-asyncio==0.24.0",\n',
        )
    )
    expect_refusal(make_engine(tmp_path), source, tmp_path / "candidate")


def test_recipe_refuses_symlinked_lock(tmp_path):
    # Shared snapshot/read_source fences already refuse any symlinked source
    # file; this records that the lock path gets no special bypass.
    source = make_lock_source(tmp_path)
    (source / "uv.lock").rename(tmp_path / "real-lock")
    (source / "uv.lock").symlink_to(tmp_path / "real-lock")
    expect_refusal(make_engine(tmp_path), source, tmp_path / "candidate")


def test_byte_identity_with_real_v4_candidate(tmp_path):
    benchmark = Path("/benchmark")
    if not (benchmark / "uv.lock").is_file():
        pytest.skip("/benchmark not mounted (host environment)")
    source = make_real_baseline(tmp_path)
    result = apply(make_engine(tmp_path), source, tmp_path / "candidate")
    candidate = Path(result["candidate_root"])
    for relative in ("pyproject.toml", ".github/workflows/ci.yml", "uv.lock"):
        produced = (candidate / relative).read_bytes()
        expected = (benchmark / relative).read_bytes()
        assert produced == expected, (
            f"{relative} differs from the real tested candidate bytes"
        )
    # Zero remaining declared metadata differences: exactly the three
    # reproduced paths changed, and no path remains declared as a refusal.
    assert result["changed_paths"] == [
        ".github/workflows/ci.yml",
        "pyproject.toml",
        "uv.lock",
    ]
    for refusal in result["declared_refusals"]:
        assert "uv.lock" not in refusal["path"]
        assert "pytest-asyncio" not in refusal["path"]


# --- round-3 corrections (Hermaguard r3 findings, implementer lane) -----------


def test_lock_lane_refuses_drifted_suite_with_old_suite_pin_on_windows(tmp_path):
    # r3 HIGH matrix-fence blind spot: a drifted suite pin plus a
    # coincidentally-equal other-job pin passed the fence, and the unanchored
    # byte-exact count==1 replace edited the WRONG job line (native windows
    # got 3.14 while the real suite stayed drifted) and reported success.
    # Built on the real baseline fixture bytes; refusal is required with NO
    # candidate and no wrong-target edit.
    source = make_real_baseline(tmp_path)
    ci = source / ".github" / "workflows" / "ci.yml"
    ci.write_bytes(
        BASELINE_CI.read_bytes()
        .replace(
            b'python-version: ["3.11", "3.12", "3.13"]',
            b'python-version: ["3.11", "3.12", "3.14"]',
            1,
        )
        .replace(
            b'python-version: ["3.12"]',
            b'python-version: ["3.11", "3.12", "3.13"]',
            1,
        )
    )
    expect_refusal(
        make_engine(tmp_path), source, tmp_path / "candidate", match="[Pp]reimage"
    )


def test_lock_lane_refuses_near_miss_extended_suite_pin(tmp_path):
    # r3 HIGH 1(c): any other standalone pin sharing the suite array's
    # opening entries in a longer (near-miss) array must be refused; the real
    # reviewed native-windows ["3.12"] single-element pin stays permitted.
    source = make_real_baseline(tmp_path)
    ci = source / ".github" / "workflows" / "ci.yml"
    ci.write_bytes(
        BASELINE_CI.read_bytes().replace(
            b'python-version: ["3.12"]',
            b'python-version: ["3.11", "3.12", "3.13", "3.15"]',
            1,
        )
    )
    expect_refusal(
        make_engine(tmp_path), source, tmp_path / "candidate", match="[Pp]reimage"
    )


def test_lock_lane_refuses_preexisting_upgrade_target_matrix_pin(tmp_path):
    # Edge r3 #4: a drifted CI already carrying a standalone pin equal to the
    # upgrade target array must refuse, otherwise the replay produces a
    # duplicate 3.14 matrix entry next to the edited suite pin.
    source = make_real_baseline(tmp_path)
    ci = source / ".github" / "workflows" / "ci.yml"
    ci.write_bytes(
        BASELINE_CI.read_bytes().replace(
            b'python-version: ["3.12"]',
            b'python-version: ["3.11", "3.12", "3.13", "3.14"]',
            1,
        )
    )
    expect_refusal(
        make_engine(tmp_path), source, tmp_path / "candidate", match="[Pp]reimage"
    )


def test_real_reviewed_shape_still_applies_with_windows_pin_carveout(tmp_path):
    # Characterisation guard for the tightened fence: the REAL reviewed
    # workflow shape (suite matrix paired with the suite os entries, the
    # native-windows ["3.12"] single pin untouched) keeps applying, with the
    # edit anchored to the fenced suite span.
    source = make_real_baseline(tmp_path)
    result = apply(make_engine(tmp_path), source, tmp_path / "candidate")
    candidate = Path(result["candidate_root"])
    produced = (candidate / ".github/workflows/ci.yml").read_text()
    assert produced.count(CI_TARGET) == 1
    assert 'python-version: ["3.12"]' in produced
    assert CI_PREIMAGE not in produced


def test_lock_delta_truncation_marker_is_out_of_band():
    # r3 LOW: the __truncated__ sentinel placed inside the bounded entries
    # dict can collide with a real package name at the 64-entry bound and
    # mask it (here "__truncated__" is a REAL package that also sorts first).
    # The mark must move out of band as {"entries": ..., "truncated": bool}.
    names = ["__truncated__"] + [f"pkg-{index:03d}" for index in range(70)]
    before = "\n".join(
        f'[[package]]\nname = "{name}"\nversion = "1.0"' for name in names
    )
    after = before.replace('version = "1.0"', 'version = "2.0"')
    delta = recipes._lock_delta(before.encode() + b"\n", after.encode() + b"\n")
    assert delta["truncated"] is True
    wrapper = delta["changed"]
    assert set(wrapper) == {"entries", "truncated"}, wrapper
    assert wrapper["truncated"] is True
    assert len(wrapper["entries"]) == recipes._MAX_LOCK_DELTA_ENTRIES
    # The real package survived in band with its true changed-pair value; the
    # old in-band sentinel would have overwritten it with None.
    assert wrapper["entries"]["__truncated__"] == ["1.0", "2.0"]
    # Non-truncated sections keep their plain shape.
    assert delta["added"] == {}
    assert delta["removed"] == {}


def test_recipe_residue_records_delta_assembly_failure(tmp_path, monkeypatch):
    # r3 MEDIUM residue-window gap: the result/lock-lane assembly (the
    # package delta build over the pinned bytes) sat OUTSIDE the post-mkdir
    # try/_residue_mark block, leaving an existing candidate root without
    # residue.json on an assembly failure. Any post-mkdir failure must mark.
    def failing_delta(before_raw, after_raw):
        raise ContractError("Simulated lock delta assembly failure")

    monkeypatch.setattr(recipes, "_lock_delta", failing_delta)
    source = make_lock_source(tmp_path)
    destination = tmp_path / "candidate"
    engine = make_engine(tmp_path)
    with pytest.raises(ContractError, match="[Aa]ssembly|[Dd]elta"):
        apply(engine, source, destination)
    monkeypatch.undo()
    assert destination.is_dir(), "failed residue must be preserved"
    residue = destination / "residue.json"
    assert residue.is_file()
    assert b"failed-residue" in residue.read_bytes()
    with pytest.raises(ContractError, match="occupied"):
        apply(engine, source, destination)


def test_artifact_bundle_fifo_behind_data_symlink_refused_nonblocking(
    tmp_path, monkeypatch
):
    # r3 LOW: the bundled artifact open lacked O_NONBLOCK, so an intermediate
    # data/ symlink pointing at a FIFO would block before the fstat class
    # checks. The open must not hang and the regular-file fence must refuse.
    package = tmp_path / "engine-package"
    package.mkdir()
    fifo_home = tmp_path / "fifo-home"
    fifo_home.mkdir()
    os.mkfifo(fifo_home / "uv.lock.v4-replay")
    (package / "data").symlink_to(fifo_home, target_is_directory=True)
    monkeypatch.setattr(recipes, "__file__", str(package / "recipes.py"))
    outcome = {}

    def probe():
        try:
            recipes._artifact_bytes()
        except ContractError as error:
            outcome["refusal"] = str(error)
        except BaseException as error:
            outcome["unexpected"] = repr(error)

    thread = threading.Thread(target=probe, daemon=True)
    thread.start()
    thread.join(5.0)
    assert not thread.is_alive(), (
        "artifact open blocked on a FIFO behind an intermediate data/ "
        "symlink (O_NONBLOCK missing)"
    )
    assert "regular" in outcome["refusal"], outcome
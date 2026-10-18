"""Fixed declarative metadata recipes (NO AI, NO dependency resolution).

The recipe is an engine-owned reviewed constant, never a caller document:
bounded exact-line edits over an explicit file allowlist with exact preimages.
Applying it copies a source tree into a fresh disposable candidate root,
re-verifying every byte against the source snapshot, and reports a bounded
per-file unified diff. Refused by design: unknown recipe ids, stale base
digests, occupied/unambiguous-destination violations, symlinks and path
escapes (identity.read_source), already-applied or drifted trees (preimage
missing), non-UTF-8 metadata and no-op edits. Lockfile and follow-up
dependency-bump updates are DECLARED REFUSALS because correct updates there
need dependency resolution (uv) and fresh artifact hashes. No subprocess,
network, uv, installation, merge or repository execution. Failed residue is
preserved and can never be reused as a candidate.
"""

import difflib
import hashlib
import json
import os
import re
import tomllib
from pathlib import Path

from .identity import read_source, snapshot
from .jsonio import ContractError, dumps

RECIPE_ID = "python314-fastapi-metadata-v1"
_MAX_DIFF_CHARS = 20000
_HEX = re.compile(r"[a-f0-9]{64}")

# Parsed-value preimages for every field the recipe actually touches. The
# line-level preimages below are substring tokens: a matching literal inside a
# TOML comment or a stale comment line can satisfy a token fence while the REAL
# field value differs. These parsed fences are checked against the actual
# parsed metadata before any candidate materialises.
_PYPROJECT_PREIMAGE = {"requires-python": ">=3.11,<3.14"}
_CLASSIFIER_PREIMAGE = (
    "Programming Language :: Python :: 3.13",
    "Topic :: Communications",
)
_DASHBOARD_PREIMAGE = ["fastapi==0.115.6"]
_DEV_PINS_PREIMAGE = ("fastapi==0.115.6", "httpx==0.27.2")
_MATRIX_PREIMAGE = ["3.11", "3.12", "3.13"]

DECLARED_REFUSALS = [
    {
        "path": "uv.lock",
        "reason": "lockfile update requires dependency resolution (uv and "
        "package-index artifact hashes); out of the fixed-recipe lane, so the "
        "proposed candidate is not install-ready until the approved "
        "resolution lane refreshes it",
    },
    {
        "path": "pyproject.toml test-dependency pins (pytest-asyncio, starlette)",
        "reason": "the separately validated v4 dependency follow-up lane "
        "(pytest-asyncio 1.4.0 with starlette 0.52.1 lock) is outside this "
        "recipe's reviewed scope",
    },
]

RECIPE = {
    "schema_version": 1,
    "id": RECIPE_ID,
    "description": "Declare Python 3.14 support and FastAPI/httpx compatibility "
    "in metadata files (dependency lockfiles excluded).",
    "files": {
        "pyproject.toml": [
            {
                "find": 'requires-python = ">=3.11,<3.14"',
                "replace": 'requires-python = ">=3.11,<3.15"',
            },
            {
                "find": '    "Programming Language :: Python :: 3.13",\n'
                '    "Topic :: Communications",',
                "replace": '    "Programming Language :: Python :: 3.13",\n'
                '    "Programming Language :: Python :: 3.14",\n'
                '    "Topic :: Communications",',
            },
            {
                "find": 'dashboard = ["fastapi==0.115.6"]',
                "replace": 'dashboard = ["fastapi==0.133.1"]',
            },
            {
                "find": '    "fastapi==0.115.6",\n    "httpx==0.27.2",',
                "replace": '    "fastapi==0.133.1",\n    "httpx==0.28.1",',
            },
        ],
        ".github/workflows/ci.yml": [
            {
                "find": 'python-version: ["3.11", "3.12", "3.13"]',
                "replace": 'python-version: ["3.11", "3.12", "3.13", "3.14"]',
            },
        ],
    },
}


def recipe_digest():
    if RECIPE["schema_version"] != 1 or RECIPE["id"] != RECIPE_ID:
        raise ContractError("Recipe contract is invalid")
    for path, edits in RECIPE["files"].items():
        if type(path) is not str or not edits:
            raise ContractError("Recipe contract is invalid")
        for edit in edits:
            if type(edit) is not dict or set(edit) != {"find", "replace"}:
                raise ContractError("Recipe contract is invalid")
            if not edit["find"] or edit["find"] == edit["replace"]:
                raise ContractError("Recipe contract is invalid")
    return hashlib.sha256(dumps(RECIPE)).hexdigest()


def _validate_pyproject_preimage(text):
    try:
        meta = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ContractError(
            "Recipe source pyproject.toml is not valid TOML (malformed or "
            "duplicate keys refused): " + str(error)[:200]
        ) from error
    project = meta.get("project")
    if type(project) is not dict:
        raise ContractError("Recipe preimage mismatch: [project] section missing")
    if project.get("requires-python") != _PYPROJECT_PREIMAGE["requires-python"]:
        raise ContractError("Recipe preimage mismatch: parsed requires-python value")
    classifiers = project.get("classifiers")
    if type(classifiers) is not list or any(
        classifier not in classifiers for classifier in _CLASSIFIER_PREIMAGE
    ):
        raise ContractError("Recipe preimage mismatch: parsed classifier values")
    optional = project.get("optional-dependencies")
    if type(optional) is not dict or optional.get("dashboard") != _DASHBOARD_PREIMAGE:
        raise ContractError("Recipe preimage mismatch: parsed dashboard pins")
    groups = meta.get("dependency-groups")
    dev = groups.get("dev", []) if type(groups) is dict else None
    if type(dev) is not list or any(pin not in dev for pin in _DEV_PINS_PREIMAGE):
        raise ContractError("Recipe preimage mismatch: parsed dev dependency pins")


def _validate_matrix_preimage(text):
    pins_pattern = re.compile(r"(?m)^\s*python-version:\s*(\[[^\]\n]*\])\s*$")
    matches = list(pins_pattern.finditer(text))
    if len(matches) != 1:
        raise ContractError(
            "Recipe preimage mismatch: expected exactly one python-version "
            f"matrix line, found {len(matches)}"
        )
    matrix = re.search(r"(?m)^\s*matrix:\s*$", text)
    if matrix is None or matches[0].start() < matrix.start():
        raise ContractError(
            "Recipe preimage mismatch: python-version line must sit inside a "
            "workflow matrix section"
        )
    try:
        pins = json.loads(matches[0].group(1))
    except (ValueError, TypeError) as error:
        raise ContractError(
            "Recipe preimage mismatch: matrix python-version is not a parseable list"
        ) from error
    if type(pins) is not list or pins != _MATRIX_PREIMAGE:
        raise ContractError("Recipe preimage mismatch: parsed matrix python-version pins")


def _validate_parsed_preimage(path, text):
    """Real parsed validation of the exact values for recipe-touched fields.

    Substring preimages can hide in comments while the real field differs, and
    malformed/duplicate-key metadata must refuse before anything materialises.
    """
    if path == "pyproject.toml":
        _validate_pyproject_preimage(text)
    elif path == ".github/workflows/ci.yml":
        _validate_matrix_preimage(text)
    else:
        raise ContractError(
            f"Recipe preimage fence unavailable for touched file {path}"
        )


def _replacements(source):
    replacements = {}
    for path, edits in RECIPE["files"].items():
        raw, _ = read_source(source, path)
        try:
            text = raw.decode()
        except UnicodeDecodeError as error:
            raise ContractError("Recipe source file is not UTF-8 text") from error
        _validate_parsed_preimage(path, text)
        body = text
        for edit in edits:
            found = body.count(edit["find"])
            if found != 1:
                raise ContractError(
                    f"Recipe preimage for {path} expected exactly once, found "
                    f"{found} (already applied or drifted tree)"
                )
            body = body.replace(edit["find"], edit["replace"], 1)
        replacements[path] = body.encode()
    return replacements


def _diff(path, before, after):
    text = "".join(
        difflib.unified_diff(
            before.decode().splitlines(keepends=True),
            after.decode().splitlines(keepends=True),
            fromfile="a/" + path,
            tofile="b/" + path,
        )
    )
    if len(text) > _MAX_DIFF_CHARS:
        text = text[:_MAX_DIFF_CHARS] + "\n... diff truncated for review\n"
    return text


def _residue_mark(destination, summary):
    try:
        raw = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(destination / "residue.json", raw, 0o600)
        try:
            os.write(fd, dumps({"state": "failed-residue", **summary}))
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        return  # keep the partial tree itself as residue; never auto-delete


def _copy(source, manifest, destination, replacements):
    for record in manifest["directories"]:
        (destination / record["path"]).mkdir(parents=True, exist_ok=True, mode=0o700)
    for record in manifest["files"]:
        raw, mode = read_source(source, record["path"])
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ContractError("Source changed during materialisation")
        target = destination / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open("xb") as stream:
            stream.write(replacements.get(record["path"], raw))
        target.chmod(mode)
    for record in sorted(
        manifest["directories"],
        key=lambda value: value["path"].count("/"),
        reverse=True,
    ):
        (destination / record["path"]).chmod(record["mode"])
    return snapshot(destination)


def apply(recipe_id, source, base_digest, destination):
    if recipe_id != RECIPE_ID:
        raise ContractError("Unknown metadata recipe")
    checked = recipe_digest()
    if type(source) is not str or not Path(source).is_absolute():
        raise ContractError("Absolute source tree required")
    if type(base_digest) is not str or not _HEX.fullmatch(base_digest):
        raise ContractError("Invalid expected base digest")
    if type(destination) is not str or not Path(destination).is_absolute():
        raise ContractError("Absolute disposable candidate destination required")
    source = Path(source)
    root = Path(destination)
    if (
        root.exists()
        or root.is_symlink()
        or root.parent.resolve() != root.parent
    ):
        raise ContractError(
            "Candidate destination is occupied or ambiguous (failed residue "
            "is preserved and never reused)"
        )
    if root.is_relative_to(source) or source.is_relative_to(root):
        raise ContractError("Candidate must be separate from source")
    manifest = snapshot(source)
    if manifest["digest"] != base_digest:
        raise ContractError(
            "Stale base: source identity differs from the expected base digest"
        )
    replacements = _replacements(source)
    root.mkdir(mode=0o700)
    # Every failure after the destination directory exists must leave a residue
    # mark (mid-copy AND post-copy reconciliation), while pre-mkdir refusals
    # keep their existing semantics and residue is never auto-deleted.
    try:
        raw_before = {path: read_source(source, path)[0] for path in replacements}
        after = _copy(source, manifest, root, replacements)
        if snapshot(source)["digest"] != manifest["digest"]:
            raise ContractError("Source changed during materialisation")
        before_files = {record["path"]: record for record in manifest["files"]}
        changed = {
            record["path"]
            for record in after["files"]
            if (record["path"], record["sha256"], record["bytes"], record["mode"])
            != (
                record["path"],
                before_files[record["path"]]["sha256"],
                before_files[record["path"]]["bytes"],
                before_files[record["path"]]["mode"],
            )
        }
        if changed != set(replacements):
            raise ContractError("Candidate changes differ from the declared recipe edits")
        diffs = {
            path: _diff(path, raw, replacements[path]) for path, raw in raw_before.items()
        }
    except BaseException as error:
        _residue_mark(
            root, {"error": str(error)[:500], "source_digest": manifest["digest"]}
        )
        if isinstance(error, OSError) and not isinstance(error, ContractError):
            raise ContractError(
                "Candidate materialisation failed: " + str(error)[:200]
            ) from error
        raise
    return {
        "schema_version": 1,
        "recipe_id": RECIPE_ID,
        "recipe_digest": checked,
        "source_digest": manifest["digest"],
        "candidate_root": str(root),
        "candidate_digest": after["digest"],
        "changed_paths": sorted(changed),
        "unchanged_paths_preserved": True,
        "diff": diffs,
        "declared_refusals": DECLARED_REFUSALS,
        "approved": False,
        "execution_performed": False,
        "install_performed": False,
        "merges_performed": 0,
        "verdict": "NOT_PROVEN",
    }
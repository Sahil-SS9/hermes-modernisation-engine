"""Fixed declarative metadata recipes (NO AI, NO dependency resolution).

The recipe is an engine-owned reviewed constant, never a caller document:
bounded exact-line edits over an explicit file allowlist with exact preimages,
plus a uv.lock REPLAY lane: the engine ingests the owner-REVIEWED,
already-TESTED v4 upgraded lockfile bytes as a hash-bound, provenance-carrying
DATA artifact under engine-owned sources and applies them as a byte-exact
replacement, gated by a digest-based preimage. The lane REPLAYS one reviewed
result; it performs NO dependency resolution - a genuinely new resolution
needs a separately scoped, signature-gated lane.
Applying the recipe copies a source tree into a fresh disposable candidate
root, re-verifying every byte against the source snapshot, and reports a
bounded per-file unified diff plus a package-level lock delta; the replayed
lock's candidate bytes are the review surface for the lock itself (the full
line-level lock diff is deliberately omitted).
Refused by design: unknown recipe ids, stale base digests,
occupied/unambiguous-destination violations, symlinks and path escapes
(identity.read_source), already-applied or drifted trees (preimage missing),
lock digests that match neither the recorded baseline nor the artifact
(drifted/resolved), tampered artifact bytes (checked against the pinned
reviewed sha256 before anything materialises), malformed/already-upgraded
metadata, and non-UTF-8 metadata. No subprocess, network, uv resolution,
installation, merge or repository execution. Failed residue is preserved and
can never be reused as a candidate.
"""

import difflib
import hashlib
import json
import os
import re
import stat
import tomllib
from pathlib import Path

from .identity import MAX_FILE_BYTES, read_source, snapshot
from .jsonio import ContractError, dumps

RECIPE_ID = "python314-fastapi-metadata-v1"
_MAX_DIFF_CHARS = 20000
_MAX_LOCK_DELTA_ENTRIES = 64
_HEX = re.compile(r"[a-f0-9]{64}")

# uv.lock replay lane: hash-bound review-verified data artifact. The bytes
# bundled at src/hermes_modernisation/data/uv.lock.v4-replay are the
# owner-tested v4 candidate lock (clone commit c6134c20f66122347f61b93fa133cf47521d6700
# on the test/modernisation-fastapi candidate lineage cc191ca...), captured
# read-only from the isolated benchmark clone. The lane applies them
# byte-exactly when the target lock hashes to the recorded baseline digest.
LOCK_PATH = "uv.lock"
LOCK_ARTIFACT_FILE = "uv.lock.v4-replay"
_LOCK_BASELINE_SHA256 = "a28285e4787ac1a478a3fc1942b55b4c631678c201566276a3b73d23154b2396"
_LOCK_ARTIFACT_SHA256 = "a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25"
LOCK_LANE = {
    "kind": "reviewed-artifact-replay",
    "path": LOCK_PATH,
    "artifact_file": LOCK_ARTIFACT_FILE,
    "baseline_sha256": _LOCK_BASELINE_SHA256,
    "artifact_sha256": _LOCK_ARTIFACT_SHA256,
    "replays": "the owner-reviewed, already-tested v4 dependency follow-up run "
    "(pytest-asyncio 1.4.0 with starlette 0.52.1 lock upgrade, 20/20 with 0 "
    "warnings on Python 3.14); this lane REPLAYS that verified result and "
    "performs NO dependency resolution",
    "source_run": "v4 dependency follow-up: RESULT-v4-20261017.txt; receipts "
    "run-v4-20261017/ with SHA256SUMS under the operator evidence directory",
    "candidate_lineage": "benchmark clone branch test/modernisation-fastapi: "
    "candidate commit cc191ca18e7529097c2cb3095ca8b803957f5598, then v4 lock "
    "follow-up commit c6134c20f66122347f61b93fa133cf47521d6700; baseline "
    "bdbc72300bb494a393992bf4b49259c06811c2b9",
    "performs_dependency_resolution": False,
}

# Parsed-value preimages for every field the recipe actually touches.
_PYPROJECT_PREIMAGE = {"requires-python": ">=3.11,<3.14"}
_CLASSIFIER_PREIMAGE = (
    "Programming Language :: Python :: 3.13",
    "Topic :: Communications",
)
_DASHBOARD_PREIMAGE = ["fastapi==0.115.6"]
_DEV_PINS_PREIMAGE = ("fastapi==0.115.6", "httpx==0.27.2", "pytest-asyncio==0.24.0")
_DEV_PINS_TARGET = ("fastapi==0.133.1", "httpx==0.28.1", "pytest-asyncio==1.4.0")
_MATRIX_PREIMAGE = ["3.11", "3.12", "3.13"]
_MATRIX_SUITE_OS = ["ubuntu-latest", "macos-latest"]
# The reviewed workflow's only non-suite standalone pin (native-windows job).
_MATRIX_WINDOW_PIN = ["3.12"]

# Declared boundaries that the reviewed lane does NOT cover.
DECLARED_REFUSALS = [
    {
        "path": "dependency resolution (fresh uv resolve)",
        "reason": "the lock lane REPLAYS the owner-reviewed, already-tested v4 "
        "lock bytes by pinned digest and performs NO dependency resolution; a "
        "genuinely new resolution needs a separately scoped, signature-gated "
        "lane",
    },
]

RECIPE = {
    "schema_version": 2,
    "id": RECIPE_ID,
    "description": "Declare Python 3.14 support and FastAPI/httpx compatibility "
    "in metadata files, and replay the reviewed v4 uv.lock bytes as a "
    "hash-bound data artifact (no dependency resolution).",
    "lock": LOCK_LANE,
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
            {
                "find": '    "pytest-asyncio==0.24.0",',
                "replace": '    "pytest-asyncio==1.4.0",',
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
    if RECIPE["schema_version"] != 2 or RECIPE["id"] != RECIPE_ID:
        raise ContractError("Recipe contract is invalid")
    for path, edits in RECIPE["files"].items():
        if type(path) is not str or not edits:
            raise ContractError("Recipe contract is invalid")
        for edit in edits:
            if type(edit) is not dict or set(edit) != {"find", "replace"}:
                raise ContractError("Recipe contract is invalid")
            if not edit["find"] or edit["find"] == edit["replace"]:
                raise ContractError("Recipe contract is invalid")
    lane = RECIPE["lock"]
    if type(lane) is not dict or set(lane) != set(LOCK_LANE):
        raise ContractError("Recipe contract is invalid")
    if (
        lane["path"] != LOCK_PATH
        or lane["artifact_file"] != LOCK_ARTIFACT_FILE
        or not _HEX.fullmatch(lane["baseline_sha256"])
        or not _HEX.fullmatch(lane["artifact_sha256"])
        or type(lane["replays"]) is not str
        or not lane["replays"]
        or type(lane["source_run"]) is not str
        or not lane["source_run"]
        or type(lane["candidate_lineage"]) is not str
        or not lane["candidate_lineage"]
        or lane["performs_dependency_resolution"] is not False
    ):
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
    if type(dev) is not list:
        raise ContractError("Recipe preimage mismatch: parsed dev dependency pins")
    # Exact reviewed preimage state, not membership: a tree carrying BOTH the
    # preimage pin and its target pin (or a duplicated preimage pin) must
    # refuse, otherwise the replay yields a duplicate target pin.
    for pin in _DEV_PINS_PREIMAGE:
        if dev.count(pin) != 1:
            raise ContractError(
                "Recipe preimage mismatch: parsed dev dependency pins (each "
                "reviewed preimage pin must be present exactly once)"
            )
    for pin in _DEV_PINS_TARGET:
        if pin in dev:
            raise ContractError(
                "Recipe preimage mismatch: the dev preimage already contains "
                "an upgrade target pin"
            )
    return None


_PINS_PATTERN = re.compile(r"(?m)^(\s*)python-version:\s*(\[[^\]\n]*\])\s*$")
_MATRIX_PATTERN = re.compile(r"(?m)^(\s*)matrix:\s*$")
_OS_PATTERN = re.compile(r"(?m)^(\s*)os:\s*(\[[^\]\n]*\])\s*$")


def _workflow_list(inner):
    """Bounded scalar-list parse for workflow os entries (plain YAML scalars)."""
    parts = [part.strip() for part in inner.strip().strip("[]").split(",")]
    if any(not part for part in parts):
        raise ContractError(
            "Recipe preimage mismatch: workflow os list has an empty entry"
        )
    values = []
    for part in parts:
        if len(part) >= 2 and part[0] == part[-1] and part[0] in ('"', "'"):
            part = part[1:-1]
        values.append(part)
    return values


def _matrix_target_pins():
    """The upgrade target array, derived from the single reviewed CI edit."""
    edit = RECIPE["files"][".github/workflows/ci.yml"][0]
    prefix = "python-version: "
    if not edit["replace"].startswith(prefix):
        raise ContractError("Recipe contract is invalid: matrix edit shape")
    try:
        pins = json.loads(edit["replace"][len(prefix):])
    except (ValueError, TypeError) as error:
        raise ContractError("Recipe contract is invalid: matrix target pins") from error
    return pins


def _enclosing_matrix(text, pin_match):
    """The matrix: mapping line enclosing a pinned line, or None."""
    candidates = [
        matrix
        for matrix in _MATRIX_PATTERN.finditer(text)
        if matrix.start() < pin_match.start()
        and len(matrix.group(1)) < len(pin_match.group(1))
    ]
    return candidates[-1] if candidates else None


def _matrix_block(text, matrix):
    """Content rows of the matrix mapping (deeper indented or blank)."""
    matrix_indent = len(matrix.group(1))
    rows = []
    for row in text[matrix.end():].splitlines():
        if not row.strip():
            rows.append(row)
            continue
        if len(row) - len(row.lstrip()) <= matrix_indent:
            break
        rows.append(row)
    return "\n".join(rows)


def _apply_anchored_matrix_edit(text, span, edit):
    """Replace exactly inside the fence-asserted span, never by body search."""
    prefix = "python-version: "
    if not edit["find"].startswith(prefix) or not edit["replace"].startswith(prefix):
        raise ContractError("Recipe contract is invalid: matrix edit shape")
    preimage_bracket = edit["find"][len(prefix):]
    target_bracket = edit["replace"][len(prefix):]
    start, end = span
    if text[start:end] != preimage_bracket:
        raise ContractError(
            "Recipe preimage mismatch: fenced matrix span drifted before the "
            "anchored edit"
        )
    body = text[:start] + target_bracket + text[end:]
    if body.count(edit["replace"]) != 1:
        raise ContractError(
            "Recipe preimage mismatch: anchored matrix edit did not yield "
            "exactly one upgrade target pin"
        )
    return body


def _validate_matrix_preimage(text):
    """Parsed fence for the CI workflow python-version matrices (anchored).

    Returns the exact bracket span of the single reviewed suite pin so the
    edit is applied only inside the fence-asserted span. The fence is exactly
    one bracketed pin EQUAL to the reviewed suite pin, NOT exactly one pin
    line: the real reviewed workflow keeps other jobs' own pins (the native
    Windows ["3.12"] matrix). The suite hit is bound to its real reviewed job
    shape: the enclosing matrix block must pair the pin with the reviewed
    suite os entries, otherwise a drifted suite plus a coincidentally-equal
    other-job pin would pass and the byte-exact replace would edit the wrong
    job. Any other standalone pin must stay the reviewed native-windows
    single-element pin; a pin equal to the upgrade target, or a longer
    near-miss array sharing the suite pin's opening entries, is refused
    pre-edit (it already is - or would become - a duplicate target matrix).
    """
    suite_hits = []
    others = []
    for match in _PINS_PATTERN.finditer(text):
        try:
            pins = json.loads(match.group(2))
        except (ValueError, TypeError) as error:
            raise ContractError(
                "Recipe preimage mismatch: matrix python-version is not a "
                "parseable list"
            ) from error
        if type(pins) is not list or any(type(pin) is not str for pin in pins):
            raise ContractError(
                "Recipe preimage mismatch: matrix python-version is not a string list"
            )
        if pins == _MATRIX_PREIMAGE:
            suite_hits.append(match)
        else:
            others.append(pins)
    if len(suite_hits) != 1:
        raise ContractError(
            "Recipe preimage mismatch: expected exactly one python-version "
            f"matrix line with pins {_MATRIX_PREIMAGE}, found {len(suite_hits)}"
        )
    suite = suite_hits[0]
    matrix = _enclosing_matrix(text, suite)
    if matrix is None:
        raise ContractError(
            "Recipe preimage mismatch: python-version line must sit inside a "
            "workflow matrix section"
        )
    suite_pairs = any(
        _workflow_list(os_match.group(2)) == _MATRIX_SUITE_OS
        for os_match in _OS_PATTERN.finditer(_matrix_block(text, matrix))
    )
    if not suite_pairs:
        raise ContractError(
            "Recipe preimage mismatch: the suite matrix block does not pair "
            f"the python-version pin with the reviewed os entries "
            f"{_MATRIX_SUITE_OS}"
        )
    for pins in others:
        if pins != _MATRIX_WINDOW_PIN:
            if pins == _matrix_target_pins():
                raise ContractError(
                    "Recipe preimage mismatch: a standalone python-version pin "
                    "already equals the upgrade target matrix (post-edit "
                    "duplicate matrix entry refused)"
                )
            if (
                pins[:2] == _MATRIX_PREIMAGE[:2]
                and len(pins) >= len(_MATRIX_PREIMAGE)
            ):
                raise ContractError(
                    "Recipe preimage mismatch: near-miss python-version pin "
                    "shares the suite array's opening entries with a longer "
                    "array (drifted or colliding pin refused)"
                )
    return (suite.start(2), suite.end(2))


def _validate_parsed_preimage(path, text):
    """Real parsed validation of the exact values for recipe-touched fields.

    Substring preimages can hide in comments while the real field differs, and
    malformed/duplicate-key metadata must refuse before anything materialises.
    Returns the anchored replacement span for matrix-touched files, else None;
    the caller must apply that edit inside the fence-asserted span only.
    """
    if path == "pyproject.toml":
        return _validate_pyproject_preimage(text)
    elif path == ".github/workflows/ci.yml":
        return _validate_matrix_preimage(text)
    else:
        raise ContractError(
            f"Recipe preimage fence unavailable for touched file {path}"
        )


def _artifact_bytes():
    """Load and hash-verify the bundled replay artifact (fail-closed)."""
    path = Path(__file__).resolve().with_name("data") / LOCK_ARTIFACT_FILE
    try:
        # O_NONBLOCK keeps the open non-hanging (same pattern as
        # evidence._read_output / identity.read_source): an intermediate
        # data/ symlink pointing at a FIFO must not block before the fstat
        # class checks below run.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ContractError(
            "Lock artifact bundle unreadable: " + type(error).__name__
        ) from error
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > MAX_FILE_BYTES
        ):
            raise ContractError(
                "Lock artifact bundle must be a regular single-link file under "
                "the size limit"
            )
        raw = bytearray()
        while True:
            chunk = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_FILE_BYTES:
                raise ContractError("Lock artifact bundle size limit exceeded")
    finally:
        os.close(fd)
    if hashlib.sha256(raw).hexdigest() != _LOCK_ARTIFACT_SHA256:
        raise ContractError(
            "Lock artifact tamper: the bundled uv.lock bytes do not match the "
            "pinned reviewed artifact sha256; replay refused"
        )
    return bytes(raw)


def _lock_replacement(source):
    """Digest-based preimage for the uv.lock replay lane.

    Refuses: absent/symlinked/oversized locks (identity.read_source), locks
    already matching the artifact (completed-already) and any other lock
    bytes (drifted or resolved elsewhere). Tamper checks the bundled artifact
    before anything materialises. Returns (baseline_bytes, artifact_bytes).
    """
    raw, _mode = read_source(source, LOCK_PATH)
    current = hashlib.sha256(raw).hexdigest()
    if current == _LOCK_ARTIFACT_SHA256:
        raise ContractError(
            "uv.lock already matches the reviewed artifact bytes: the tree was "
            "already upgraded; re-applying the same replay is refused"
        )
    if current != _LOCK_BASELINE_SHA256:
        raise ContractError(
            "uv.lock preimage mismatch: the current lock does not hash to the "
            "recorded baseline digest (drifted or resolved elsewhere); the "
            "byte-exact reviewed replay does not define an update for it, and "
            "dependency resolution is out of scope"
        )
    return raw, _artifact_bytes()


def _lock_packages(raw):
    try:
        data = tomllib.loads(raw.decode())
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ContractError(
            "Lock replay data is not parseable uv.lock TOML (refused): "
            + str(error)[:200]
        ) from error
    packages = data.get("package")
    if type(packages) is not list:
        raise ContractError("Lock replay data has no package table")
    result = {}
    for entry in packages:
        if type(entry) is not dict or "name" not in entry:
            raise ContractError("Lock replay data has a malformed package entry")
        name = entry["name"]
        if type(name) is not str or not name:
            raise ContractError("Lock replay data has an invalid package name")
        if name in result:
            raise ContractError("Lock replay data has duplicate package entries")
        version = entry.get("version")
        if version is not None and type(version) is not str:
            raise ContractError("Lock replay data has an invalid package version")
        result[name] = version
    return result


def _lock_delta(before_raw, after_raw):
    """Usable package-level delta summary (NOT a line-level lock diff)."""
    old = _lock_packages(before_raw)
    new = _lock_packages(after_raw)
    changed = {}
    added = {}
    removed = {}
    for name in sorted(set(old) | set(new)):
        before, after = old.get(name), new.get(name)
        if before == after:
            continue
        if before is None:
            added[name] = after
        elif after is None:
            removed[name] = before
        else:
            changed[name] = [before, after]
    delta = {}
    truncated = False
    for label, entries in (
        ("changed", changed),
        ("added", added),
        ("removed", removed),
    ):
        if len(entries) > _MAX_LOCK_DELTA_ENTRIES:
            # Out-of-band truncation mark: bounded entries live under
            # "entries" with the boolean beside them. An in-band
            # "__truncated__" key could collide with a real package name at
            # the bound and silently mask it.
            delta[label] = {
                "entries": dict(sorted(entries.items())[: _MAX_LOCK_DELTA_ENTRIES]),
                "truncated": True,
            }
            truncated = True
        else:
            delta[label] = entries
    delta["truncated"] = truncated
    return delta


def _replacements(source):
    replacements = {}
    lock_before = None
    for path, edits in RECIPE["files"].items():
        raw, _ = read_source(source, path)
        try:
            text = raw.decode()
        except UnicodeDecodeError as error:
            raise ContractError("Recipe source file is not UTF-8 text") from error
        span = _validate_parsed_preimage(path, text)
        if span is not None:
            # Anchored matrix edit: the bytes change ONLY inside the
            # fence-asserted suite-pin span, never by a whole-body substring
            # search (a coincidentally-equal other-job pin must not be edited).
            if len(edits) != 1:
                raise ContractError(
                    "Recipe contract is invalid: the anchored matrix file "
                    "must carry a single reviewed edit"
                )
            edit = edits[0]
            found = text.count(edit["find"])
            if found != 1:
                raise ContractError(
                    f"Recipe preimage for {path} expected exactly once, found "
                    f"{found} (already applied or drifted tree)"
                )
            body = _apply_anchored_matrix_edit(text, span, edit)
        else:
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
    if "lock" in RECIPE:
        lock_before, replacements[LOCK_PATH] = _lock_replacement(source)
    return replacements, lock_before


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
    replacements, lock_before = _replacements(source)
    root.mkdir(mode=0o700)
    # Every failure after the destination directory exists must leave a residue
    # mark - mid-copy, post-copy reconciliation AND the result/lock-lane
    # assembly below (the package delta build over the pinned bytes) - while
    # pre-mkdir refusals keep their existing semantics and residue is never
    # auto-deleted.
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
            path: _diff(path, raw, replacements[path])
            for path, raw in raw_before.items()
            if path != LOCK_PATH
        }
        result = {
            "schema_version": 2,
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
            "resolution_performed": False,
            "install_performed": False,
            "merges_performed": 0,
            "verdict": "NOT_PROVEN",
        }
        if lock_before is not None:
            lane = RECIPE["lock"]
            result["lock_lane"] = {
                key: lane[key]
                for key in (
                    "kind",
                    "replays",
                    "source_run",
                    "candidate_lineage",
                    "performs_dependency_resolution",
                )
            }
            result["lock_lane"]["path"] = LOCK_PATH
            result["lock_lane"]["baseline_sha256"] = _LOCK_BASELINE_SHA256
            result["lock_lane"]["artifact_sha256"] = _LOCK_ARTIFACT_SHA256
            result["lock_lane"]["package_delta"] = _lock_delta(
                lock_before, replacements[LOCK_PATH]
            )
            result["lock_lane"]["diff_surface"] = (
                "candidate lock bytes are byte-exact replays of the reviewed "
                "artifact; the line-level unified diff is omitted and the "
                "candidate bytes are the review surface, summarised by the "
                "package-level package_delta"
            )
        return result
    except BaseException as error:
        _residue_mark(
            root, {"error": str(error)[:500], "source_digest": manifest["digest"]}
        )
        if isinstance(error, OSError) and not isinstance(error, ContractError):
            raise ContractError(
                "Candidate materialisation failed: " + str(error)[:200]
            ) from error
        raise
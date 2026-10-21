"""Data-only source-replacement proposals and isolated candidate materialisation.

No LLM, shell, install, owner approval or execution. Dependency/build files need
a separate trusted migration contract; this initial lane refuses their edits.
"""

import hashlib
import re
from pathlib import Path
from .identity import snapshot, read_source, safe_relative
from .jsonio import ContractError, dumps, loads

FIELDS = {
    "schema_version",
    "source_digest",
    "goal",
    "changes",
    "allowed_paths",
    "planned_differences",
}
PROTECTED = {
    "tests",
    "test",
    "fixtures",
    "evidence",
    "oracle",
    "oracles",
    "schemas",
    ".github",
}
FILES = {
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "setup.py",
    "setup.cfg",
    "conftest.py",
    "oracle.json",
    "Dockerfile",
    "Makefile",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Gemfile",
    "Gemfile.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "composer.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lock",
    "bun.lockb",
    "deno.lock",
    "flake.nix",
    "flake.lock",
}
BUILD_PREFIXES = ("Dockerfile.", "docker-compose.")
REQUIREMENTS_FILE = re.compile(r"requirements(?:[._-][^/]+)?\.(?:txt|in)\Z")
FILES_LOWER = {item.lower() for item in FILES}


def _dependency_manifest(parts):
    """Recognise dependency manifests without matching ordinary source modules."""
    if not parts:
        return False
    name = parts[-1].lower()
    if name in FILES_LOWER:
        return True
    if REQUIREMENTS_FILE.fullmatch(name):
        return True
    return (
        len(parts) > 1
        and any(part.lower() == "requirements" for part in parts[:-1])
        and name.endswith((".txt", ".in"))
    )


def forbidden_edit(path):
    """Return why a path is outside this lane, or None when it is permitted."""
    parts = Path(path).parts
    name = Path(path).name
    if any(part in PROTECTED for part in parts):
        return "protected directory"
    if any(part.startswith(".") for part in parts):
        return "hidden path"
    if _dependency_manifest(parts) or name.startswith(BUILD_PREFIXES):
        return "dependency, build or test manifest"
    if name.startswith("test_"):
        return "test file"
    return None


def validate_proposal(source, proposal):
    proposal = loads(dumps(proposal))
    if (
        set(proposal) != FIELDS
        or type(proposal["schema_version"]) is not int
        or proposal["schema_version"] != 1
    ):
        raise ContractError("Unsupported or unknown proposal fields")
    if type(proposal["goal"]) is not str or not 1 <= len(proposal["goal"]) <= 4000:
        raise ContractError("Bounded migration goal required")
    if proposal["planned_differences"] != []:
        raise ContractError(
            "Planned behavioural differences require a separate owner contract; unavailable"
        )
    paths = proposal["allowed_paths"]
    changes = proposal["changes"]
    if (
        type(paths) is not list
        or not 1 <= len(paths) <= 100
        or len(set(paths)) != len(paths)
    ):
        raise ContractError("Bounded distinct path allowlist required")
    if type(changes) is not list or not 1 <= len(changes) <= 100:
        raise ContractError("Bounded changes required")
    manifest = snapshot(Path(source))
    if manifest["digest"] != proposal["source_digest"]:
        raise ContractError("Proposal source identity is stale")
    names = set()
    total = 0
    for change in changes:
        if type(change) is not dict or set(change) != {
            "path",
            "before_sha256",
            "replacement",
        }:
            raise ContractError("Invalid source replacement")
        path = safe_relative(change["path"])
        if (
            path not in paths
            or path in names
            or forbidden_edit(path) is not None
        ):
            raise ContractError("Protected, duplicate or out-of-contract edit")
        if not re.fullmatch(r"[a-f0-9]{64}", change["before_sha256"]):
            raise ContractError("Expected source digest required")
        raw, _ = read_source(source, path)
        if hashlib.sha256(raw).hexdigest() != change["before_sha256"]:
            raise ContractError("Original source bytes changed")
        if type(change["replacement"]) is not str:
            raise ContractError("Replacement must be literal text")
        replacement = change["replacement"].encode("utf-8")
        total += len(replacement)
        if total > 524288 or b"\0" in replacement:
            raise ContractError("Replacement payload limit exceeded")
        names.add(path)
    if set(paths) != names:
        raise ContractError(
            "Every allowlisted path requires exactly one explicit change"
        )
    return proposal, manifest


def stage_candidate(source, destination, proposal):
    source = Path(source)
    destination = Path(destination)
    proposal, manifest = validate_proposal(source, proposal)
    if (
        not destination.is_absolute()
        or destination.exists()
        or destination.is_symlink()
        or destination.parent.resolve() != destination.parent
    ):
        raise ContractError("Fresh unambiguous candidate destination required")
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ContractError("Candidate must be separate from source")
    destination.mkdir(mode=0o700)
    # Keep a partial candidate after failure for diagnosis; never overwrite/reuse it.
    for record in manifest["directories"]:
        (destination / record["path"]).mkdir(parents=True, exist_ok=True, mode=0o700)
    replacements = {
        change["path"]: change["replacement"].encode() for change in proposal["changes"]
    }
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
    after = snapshot(destination)
    if snapshot(source)["digest"] != manifest["digest"]:
        raise ContractError("Source changed during materialisation")
    changed = {
        record["path"]
        for record in manifest["files"]
        if next(item for item in after["files"] if item["path"] == record["path"])
        != record
    }
    if changed - set(replacements):
        raise ContractError("Unexpected candidate changes")
    return {
        "schema_version": 1,
        "source_digest": manifest["digest"],
        "candidate_digest": after["digest"],
        "proposal_digest": hashlib.sha256(dumps(proposal)).hexdigest(),
        "changed_paths": sorted(changed),
        "approved": False,
        "execution_performed": False,
        "verdict": "NOT_PROVEN",
    }

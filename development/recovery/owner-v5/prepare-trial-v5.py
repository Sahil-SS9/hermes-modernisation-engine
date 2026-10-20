#!/usr/bin/env python3
"""Prepare the trial-v5 owner approval directory.

Sequence: verify every pinned identity against the engine's committed HEAD, clone a
fresh disposable copy of the pinned baseline, assess it with the engine, apply the
engine's reviewed recipe to a fresh candidate root, build the two pinned container
images (network scoped to dependency sync only), stage two one-use signed-grant
requests, and generate the owner signing script.

Preparation only: no sandbox execution, no grant use, no signature handling.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

CONTROL = Path("/home/kensei/projects/modernisation-benchmarks/control")
TRIAL_ROOT = CONTROL / "trial-v5"
ENGINE = Path("/home/kensei/repos/hermes-modernisation-engine")
ORIGINAL = Path("/home/kensei/repos/hermes-walkie-talkie")
ORACLE = CONTROL / "walkie-regression-oracle-v2.json"
ENROLLED_PEM = CONTROL / "owner-public-key.pem"
ENROLMENT = CONTROL / "owner-enrolment.json"
V4_EVIDENCE = Path(
    "/home/kensei/handoff/agent-plugin-plans/evidence/modernisation-first-upgrade/"
    "run-v4-20261017/candidate-eb0625ba998a4d7d9cb6c5e34e42695d"
)

DISPOSABLE = TRIAL_ROOT / "disposable"
CLONE = DISPOSABLE / "source-clone"
CANDIDATE_ROOT = DISPOSABLE / "candidate-v5"
CONTEXT_BASELINE = DISPOSABLE / "context-baseline"
CONTEXT_CANDIDATE = DISPOSABLE / "context-candidate"
EXEC_ROOT = TRIAL_ROOT / "owner-executor-v5"
ENGINE_DATA = EXEC_ROOT / "engine-data"
LEDGER = EXEC_ROOT / "claims" / "claims.sqlite"
REQUESTS_ROOT = TRIAL_ROOT / "requests"
SIGNING_SCRIPT = TRIAL_ROOT / "sign-owner-trial-v5.sh"
TEMPLATE = TRIAL_ROOT / "templates" / "sign-owner-trial-v5.sh.tmpl"
SIGN_DIR = "/home/sahil/trial-v5-signatures"

ENGINE_COMMIT = "c343e0bbb26f613571dd03602321b74b08b4ecf2"
ENGINE_BRANCH = "build/phase0"
ENGINE_CORE_DIGEST = "d2d28f63cb552a49b2a35f4b6b7b988980a019a298714cabfd3b2c6aab82afdd"
ORIGINAL_HEAD = "bdbc72300bb494a393992bf4b49259c06811c2b9"
ORACLE_SHA = "cfc9d94ef38de1b7a8053fca346ff861e6d823c908877fb45be2829084891275"
EXPECTATION_SHA = "e63330dd940a00cb399dfa8d7b0c27238c9df6f28d64a1da7eb6359c1c7e1353"
PRODUCER_SHA = "4020189b0da02a476e012a7a35d48ee6595053d03d73053675c539178133e8d9"
RECIPE_ID = "python314-fastapi-metadata-v1"
RECIPE_DIGEST = "5431b36457d938703517f0b878ee514aa2384ed0062f49da22d5aae1d4773c61"
LOCK_BASELINE_SHA = "a28285e4787ac1a478a3fc1942b55b4c631678c201566276a3b73d23154b2396"
LOCK_ARTIFACT_SHA = "a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25"
ENROLLED_SPKI = "MCowBQYDK2VwAyEAKpMZpRxBfeT0ZqKa87hpT1kXdZCHnYK6hHqh0f6Fb+8="
ENROLLED_PEM_SHA = "1d5e9fd2722019c33ef7902022642956f6d3cc6ddbbe1337b0dbaee188dac74b"
ENROLMENT_SHA = "15e8af8d7ba140e32f43877f637f0848bb38a226a5cad597db7b1397bb68b415"
ENROLLED_RAW_SHA = "879b3909477f06cc23df5ac9b5e825e4a1d259d6a7f37c89af88b798b9a614c5"
V4_RECEIPT_SHA = "42c1cdda58dbdb9e70e41c9bf633ff14c03a690e239f14e9934dac8d367e2af1"
V4_EVALUATION_SHA = "c6c84d55d8a6140d31470be04bfa3dbc3c69e1a16e6eed45121d900e0b0288ed"
V4_JUNIT_SHA = "a40a794163b6620736e31cd97206c21b01915b4148d7965b4c72b6486fccb169"
V4_OUTPUT_SHA = "0b03d42ccf1987e72662acc23af1c9e4426805813bacd840dc6ad7fe06494083"
BASE_IMAGE_PYTHON = "python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258"
VALIDATOR_IMAGE = "modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6"
SANDBOX_DEV_IMAGE = "modernise-sandbox-dev@sha256:49808cb0b9909505e906fcef5e0ea373566c96a0508cbc3f60c2fc38de08217f"
V4_CANDIDATE_IMAGE = "modernise-walkie-candidate:v4@sha256:b3613f1f72f20834961fef5230fb80059a6f4ef6ac89464af15bc13cd9795b26"
AGENT_USER = "kensei"
ACTOR = "sahil"
GRANT_DAYS = 7
TIMEOUT_SECONDS = 120
OUTPUT_LIMIT_BYTES = 4_194_304

sys.path.insert(0, str(ENGINE / "src"))
from hermes_modernisation import approvals, evaluator, executor, recipes  # noqa: E402
from hermes_modernisation import runner  # noqa: E402
from hermes_modernisation.identity import snapshot  # noqa: E402
from hermes_modernisation.jsonio import dumps  # noqa: E402

TEST_ARGS = [
    "tests/unit/test_dashboard_api.py",
    "tests/security/test_ws_auth_fails_closed.py",
    "-o",
    "addopts=",
    "-ra",
]


class PreparationError(RuntimeError):
    pass


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _enrolled_public() -> bytes:
    key = load_pem_public_key(ENROLLED_PEM.read_bytes())
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def _verify_identities() -> dict[str, object]:
    if _git(ENGINE, "rev-parse", "HEAD") != ENGINE_COMMIT:
        raise PreparationError("engine HEAD is not the pinned commit")
    if _git(ENGINE, "branch", "--show-current") != ENGINE_BRANCH:
        raise PreparationError("engine branch is not the pinned branch")
    if _git(ENGINE, "status", "--porcelain"):
        raise PreparationError("engine worktree is not clean")
    core = snapshot(ENGINE / "src" / "hermes_modernisation")
    if core["digest"] != ENGINE_CORE_DIGEST:
        raise PreparationError("engine core digest does not match the pinned identity")
    if _git(ORIGINAL, "rev-parse", "HEAD") != ORIGINAL_HEAD:
        raise PreparationError("original walkie repo HEAD is not the pinned baseline")
    if _git(ORIGINAL, "status", "--porcelain"):
        raise PreparationError("original walkie repo worktree is not clean")
    if _sha(ORACLE) != ORACLE_SHA:
        raise PreparationError("oracle digest mismatch")
    oracle = json.loads(ORACLE.read_bytes())
    if oracle["source_commit"] != ORIGINAL_HEAD or oracle["required_test_count"] != 20:
        raise PreparationError("oracle contract does not match the pinned scope")
    expectation_path = TRIAL_ROOT / "EXPECTED-CASES-V4.json"
    if _sha(expectation_path) != EXPECTATION_SHA:
        raise PreparationError("expectation digest mismatch")
    parsed = evaluator.load_expectation(expectation_path.read_bytes())
    if len(parsed["cases"]) != 20 or parsed["skip_policy"] != "none":
        raise PreparationError("expectation is not the exact 20-case zero-skip set")
    if hashlib.sha256(runner.PROGRAM.encode()).hexdigest() != PRODUCER_SHA:
        raise PreparationError("engine producer program digest mismatch")
    if recipes.recipe_digest() != RECIPE_DIGEST or recipes.RECIPE_ID != RECIPE_ID:
        raise PreparationError("engine recipe identity mismatch at the pinned HEAD")
    if _sha(ENROLLED_PEM) != ENROLLED_PEM_SHA:
        raise PreparationError("enrolled public key digest mismatch")
    raw = _enrolled_public()
    if hashlib.sha256(raw).hexdigest() != ENROLLED_RAW_SHA:
        raise PreparationError("enrolled raw public key digest mismatch")
    spki = base64.b64encode(
        Ed25519PublicKey.from_public_bytes(raw).public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
    ).decode()
    if spki != ENROLLED_SPKI:
        raise PreparationError("enrolled SPKI mismatch")
    enrolment = json.loads(ENROLMENT.read_bytes())
    if (
        enrolment.get("public_key_spki_base64") != ENROLLED_SPKI
        or enrolment.get("actor") != ACTOR
        or enrolment.get("public_key_raw_sha256") != ENROLLED_RAW_SHA
        or enrolment.get("private_key_held_by_agent") is not False
    ):
        raise PreparationError("owner enrolment does not carry the enrolled identity")
    if _sha(ENROLMENT) != ENROLMENT_SHA:
        raise PreparationError("owner enrolment digest mismatch")
    v4 = {
        name: _sha(V4_EVIDENCE / name)
        for name in ("receipt.json", "evaluation.json", "junit.xml", "output.bin")
    }
    if (
        v4["receipt.json"] != V4_RECEIPT_SHA
        or v4["evaluation.json"] != V4_EVALUATION_SHA
        or v4["junit.xml"] != V4_JUNIT_SHA
        or v4["output.bin"] != V4_OUTPUT_SHA
    ):
        raise PreparationError("v4 provenance digests mismatch")
    return {
        "engine_commit": ENGINE_COMMIT,
        "engine_branch": ENGINE_BRANCH,
        "engine_core_digest": core["digest"],
        "original_head": ORIGINAL_HEAD,
        "oracle_sha256": ORACLE_SHA,
        "expectation_sha256": EXPECTATION_SHA,
        "expectation_case_count": len(parsed["cases"]),
        "producer_sha256": PRODUCER_SHA,
        "recipe_id": RECIPE_ID,
        "recipe_digest": RECIPE_DIGEST,
        "recipe_lock_baseline_sha256": LOCK_BASELINE_SHA,
        "recipe_lock_artifact_sha256": LOCK_ARTIFACT_SHA,
        "enrolled_actor": ACTOR,
        "enrolled_spki": ENROLLED_SPKI,
        "enrolled_pem_sha256": ENROLLED_PEM_SHA,
        "enrolment_sha256": ENROLMENT_SHA,
        "v4_provenance_sha256": v4,
        "v4_candidate_image": V4_CANDIDATE_IMAGE,
    }


def _fresh_clone() -> dict[str, object]:
    if DISPOSABLE.exists():
        raise PreparationError(f"refusing to reuse a disposable root: {DISPOSABLE}")
    DISPOSABLE.mkdir(parents=True, mode=0o700)
    subprocess.run(
        ["git", "clone", "--no-hardlinks", "--quiet", str(ORIGINAL), str(CLONE)],
        check=True,
        capture_output=True,
    )
    if _git(CLONE, "rev-parse", "HEAD") != ORIGINAL_HEAD:
        raise PreparationError("fresh clone HEAD does not match the pinned baseline")
    if _git(CLONE, "status", "--porcelain"):
        raise PreparationError("fresh clone is not clean")
    identity = snapshot(CLONE)
    return {
        "path": str(CLONE),
        "clone_command": "git clone --no-hardlinks <original> <clone>",
        "head": ORIGINAL_HEAD,
        "source_digest": identity["digest"],
        "file_count": identity["file_count"],
        "directory_count": len(identity["directories"]),
        "continuity_note": (
            "clone file content is byte-identical to the accepted v3 baseline tree "
            "(baseline-source-v2, digest 93f42193...); the identity digest differs "
            "only because the v3 prepared copy carried two extra empty directories"
        ),
    }


def _assess(clone: dict, request_id: str, created: list[Path]) -> dict[str, object]:
    if EXEC_ROOT.exists():
        raise PreparationError(f"refusing to reuse an executor root: {EXEC_ROOT}")
    EXEC_ROOT.mkdir(parents=True, mode=0o700)
    created.append(EXEC_ROOT)
    ENGINE_DATA.mkdir(parents=True, mode=0o700)
    (EXEC_ROOT / "claims").mkdir(parents=True, mode=0o700)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "hermes_modernisation",
            "--data-dir",
            str(ENGINE_DATA),
            "assess",
            "--repo",
            clone["path"],
            "--goal",
            "trial-v5: engine-in-the-loop regression trial (baseline vs recipe candidate, "
            "exact v4 20-case scope, zero-skip, NOT_PROVEN verdicts)",
            "--request-id",
            request_id,
        ],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(ENGINE / "src")},
    )
    if result.returncode:
        raise PreparationError(
            "engine assessment failed: " + (result.stderr or result.stdout)[:400]
        )
    job = json.loads(result.stdout)
    if job["assessment"]["source_digest"] != clone["source_digest"]:
        raise PreparationError("engine assessment digest does not match the fresh clone")
    return {
        "job_id": job["job_id"],
        "request_id": request_id,
        "source_digest": job["assessment"]["source_digest"],
        "data_dir": str(ENGINE_DATA),
    }


def _apply_recipe(clone: dict) -> dict[str, object]:
    result = recipes.apply(RECIPE_ID, clone["path"], clone["source_digest"], str(CANDIDATE_ROOT))
    if result["recipe_digest"] != RECIPE_DIGEST:
        raise PreparationError("recipe application digest mismatch")
    expected_changes = sorted(["pyproject.toml", ".github/workflows/ci.yml", "uv.lock"])
    if sorted(result["changed_paths"]) != expected_changes:
        raise PreparationError(f"unexpected recipe change set: {result['changed_paths']}")
    lane = result.get("lock_lane") or {}
    if lane.get("baseline_sha256") != LOCK_BASELINE_SHA or lane.get("artifact_sha256") != LOCK_ARTIFACT_SHA:
        raise PreparationError("recipe lock lane pins mismatch")
    if _sha(CANDIDATE_ROOT / "uv.lock") != LOCK_ARTIFACT_SHA:
        raise PreparationError("replayed candidate lock does not match the pinned artifact")
    if _sha(Path(clone["path"]) / "uv.lock") != LOCK_BASELINE_SHA:
        raise PreparationError("clone lock does not match the pinned recipe baseline")
    identity = snapshot(CANDIDATE_ROOT)
    if identity["digest"] != result["candidate_digest"]:
        raise PreparationError("candidate root identity does not match the apply result")
    return {
        "root": result["candidate_root"],
        "candidate_digest": result["candidate_digest"],
        "changed_paths": result["changed_paths"],
        "declared_refusals": result["declared_refusals"],
        "lock_lane": lane,
        "verdict": result["verdict"],
    }


def _build_contexts() -> None:
    for context, source in (
        (CONTEXT_BASELINE, CLONE),
        (CONTEXT_CANDIDATE, CANDIDATE_ROOT),
    ):
        context.mkdir(parents=True, mode=0o700)
        for filename in ("pyproject.toml", "README.md", "uv.lock"):
            shutil.copyfile(source / filename, context / filename)
    for filename in ("pyproject.toml", "README.md", "uv.lock"):
        blob = subprocess.run(
            ["git", "-C", str(CLONE), "cat-file", "blob", f"HEAD:{filename}"],
            capture_output=True,
            check=True,
        ).stdout
        if (CONTEXT_BASELINE / filename).read_bytes() != blob:
            raise PreparationError(f"baseline context {filename} differs from the pinned commit")
    if (CONTEXT_CANDIDATE / "uv.lock").read_bytes() != (CANDIDATE_ROOT / "uv.lock").read_bytes():
        raise PreparationError("candidate context lock mismatch")


def _build_images() -> dict[str, dict[str, str]]:
    images: dict[str, dict[str, str]] = {}
    for phase, tag, context in (
        ("baseline", "modernise-walkie-baseline:v5", CONTEXT_BASELINE),
        ("candidate", "modernise-walkie-candidate:v5", CONTEXT_CANDIDATE),
    ):
        log_path = DISPOSABLE / f"build-{phase}.log"
        build = subprocess.run(
            [
                "docker",
                "build",
                "--progress=plain",
                "-f",
                str(TRIAL_ROOT / "docker" / f"{phase}.Dockerfile"),
                "-t",
                tag,
                str(context),
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
        log_path.write_text(build.stdout + build.stderr)
        log_path.chmod(0o600)
        if build.returncode != 0:
            raise PreparationError(f"{phase} image build failed; log: {log_path}")
        inspected = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", tag],
            capture_output=True,
            text=True,
            check=True,
        )
        digests = json.loads(inspected.stdout)
        if len(digests) != 1:
            raise PreparationError(f"{phase} image has ambiguous repo digests: {digests}")
        versions = ""
        for line in (build.stdout + build.stderr).splitlines():
            if "VERSIONS " in line:
                versions = line.split("VERSIONS ", 1)[1].strip()
        if not versions:
            # cached build layers do not replay RUN output; read the versions back
            # from a throwaway container of the built image (no mounts, no network)
            python_bin = (
                "/baseline/.venv/bin/python"
                if phase == "baseline"
                else "/candidate/.venv/bin/python"
            )
            probe = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--read-only",
                    "--tmpfs",
                    "/tmp",
                    "--user",
                    "65534:65534",
                    digests[0],
                    python_bin,
                    "-B",
                    "-c",
                    "import sys,fastapi,httpx,pytest;"
                    "print('VERSIONS',sys.version.split()[0],fastapi.__version__,"
                    "httpx.__version__,pytest.__version__)",
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            for line in probe.stdout.splitlines():
                if "VERSIONS " in line:
                    versions = line.split("VERSIONS ", 1)[1].strip()
        if not versions:
            raise PreparationError(f"{phase} build did not report in-image versions")
        images[phase] = {
            "ref": digests[0],
            "tag": tag,
            "build_log": str(log_path),
            "build_log_sha256": _sha(log_path),
            "in_image_versions": versions,
        }
    return images


def _requests(
    assessment: dict,
    recipe: dict,
    images: dict,
    clone: dict,
    attempt_prefix: str,
    expires_epoch: int,
) -> dict[str, dict]:
    phases = {}
    for phase, image_ref, source in (
        ("baseline", images["baseline"]["ref"], CLONE),
        ("candidate", images["candidate"]["ref"], CANDIDATE_ROOT),
    ):
        python = "/baseline/.venv/bin/python" if phase == "baseline" else "/candidate/.venv/bin/python"
        argv = [python, "-B", "-c", runner.PROGRAM, *TEST_ARGS]
        manager = executor.Executor(None, EXEC_ROOT, image_ref, profile="default", phase=phase)
        environment = manager.environment({"argv": argv, "oracle_digest": ORACLE_SHA})
        environment_digest = hashlib.sha256(dumps(environment)).hexdigest()
        source_digest = clone["source_digest"] if phase == "baseline" else recipe["candidate_digest"]
        operation = {
            "schema_version": 1,
            "job_id": assessment["job_id"],
            "attempt_id": f"{attempt_prefix}-{phase}",
            "actor": ACTOR,
            "profile": "default",
            "source_digest": source_digest,
            "candidate_digest": source_digest,
            "oracle_digest": ORACLE_SHA,
            "environment_digest": environment_digest,
            "image_digest": image_ref.split("@sha256:")[-1],
            "argv": argv,
            "read_roots": ["/source"],
            "write_roots": ["/tmp", "/work"],
            "network": "none",
            "timeout_seconds": TIMEOUT_SECONDS,
            "output_limit_bytes": OUTPUT_LIMIT_BYTES,
        }
        approvals.validate_operation(operation)
        manager.prepare(operation, source, ORACLE)
        body = {
            "schema_version": 1,
            "operation": operation,
            "nonce": secrets.token_hex(16),
            "expires_at": expires_epoch,
            "max_uses": 1,
        }
        raw = approvals.canonical(body)
        if approvals.canonical(json.loads(raw)) != raw:
            raise PreparationError("request encoding is not canonical-stable")
        phases[phase] = {
            "body": body,
            "bytes": raw,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "attempt_id": operation["attempt_id"],
            "environment_digest": environment_digest,
            "argv_sha256": hashlib.sha256(dumps({"argv": argv})).hexdigest(),
            "image_ref": image_ref,
            "source_digest": source_digest,
        }
    return phases


def _summary_text(clone, recipe, images, expires_iso, manifest_path, runner_path, requests) -> str:
    return f"""APPROVAL: compare the original and upgraded COPIES of hermes-walkie-talkie.

- Two one-use test runs, original first; 20 selected checks on each copy.
- Isolated containers: no network during tests; at most 120 seconds per run.
- Your original project is not changed. No publishing, merging, installation
  on your machine, service restarts or live deployment is authorised.
- The copies and dependency environments were already prepared. That setup
  downloaded packages inside containers; the actual project tests have not run.
- This signs permission only. It does NOT start the tests; KENSEI runs them later.
- Your approval also signs the complete test package. If its files change after
  signing, verification refuses before either permission is used.
- A passing result covers these 20 checks only, not every possible behaviour.

Approval expires: {expires_iso}
The private key stays in your account. Only public signatures are saved for KENSEI.
"""


def _signing_script(requests, manifest_path, runner_path, expires_epoch, expires_iso, clone, recipe, images, manifest_sha) -> str:
    template = TEMPLATE.read_text()
    replacements = {
        "__MANIFEST_PATH__": str(manifest_path),
        "__RUNNER_PATH__": str(runner_path),
        "__PREPARER_PATH__": str(TRIAL_ROOT / "prepare-trial-v5.py"),
        "__EXPECTATION_PATH__": str(TRIAL_ROOT / "EXPECTED-CASES-V4.json"),
        "__MANIFEST_SHA__": manifest_sha,
        "__RUNNER_SHA__": _sha(runner_path),
        "__PREPARER_SHA__": _sha(TRIAL_ROOT / "prepare-trial-v5.py"),
        "__EXPECTATION_SHA__": _sha(TRIAL_ROOT / "EXPECTED-CASES-V4.json"),
        "__EXPIRES_EPOCH__": str(expires_epoch),
        "__EXPIRES_ISO__": expires_iso,
        "__SIGN_DIR__": SIGN_DIR,
        "__AGENT_USER__": AGENT_USER,
        "__ENROLLED_PEM__": ENROLLED_PEM.read_text().strip(),
        "__B_SHA__": requests["baseline"]["sha256"],
        "__C_SHA__": requests["candidate"]["sha256"],
        "__B_B64__": base64.b64encode(requests["baseline"]["bytes"]).decode(),
        "__C_B64__": base64.b64encode(requests["candidate"]["bytes"]).decode(),
        "__SUMMARY__": _summary_text(
            clone, recipe, images, expires_iso, manifest_path, runner_path, requests
        ),
    }
    filled = template
    for marker, value in replacements.items():
        filled = filled.replace(marker, value)
    if "__" in filled.replace("__init__", ""):
        raise PreparationError("signing script template left an unfilled marker")
    return filled


def main() -> int:
    started = time.time_ns()
    created: list[Path] = []
    try:
        identities = _verify_identities()
        if LEDGER.exists() or Path(SIGN_DIR, "trial-v5-signatures.txt").exists():
            raise PreparationError("owner approval/claim state exists; refusing to replace or reset it")
        for stale in (DISPOSABLE, EXEC_ROOT):
            if stale.exists():
                stale.rename(stale.with_name(stale.name + f".ABANDONED-partial-unsigned-{started}"))
        clone = _fresh_clone()
        created.append(DISPOSABLE)
        request_id = f"trial-v5-{started}"
        assessment = _assess(clone, request_id, created)
        recipe = _apply_recipe(clone)
        _build_contexts()
        images = _build_images()
        expires_epoch = int(time.time()) + GRANT_DAYS * 86400
        expires_iso = datetime.fromtimestamp(expires_epoch, timezone.utc).isoformat(timespec="seconds")
        requests = _requests(assessment, recipe, images, clone, f"trial-v5-{started}", expires_epoch)
        runner_sha = _sha(TRIAL_ROOT / "run-trial-v5.py")
        approval_dir = REQUESTS_ROOT / f"trial-v5-{started}"
        approval_dir.mkdir(parents=True, mode=0o755)
        created.append(approval_dir)
        manifest = {
            "schema_version": 1,
            "trial": "trial-v5",
            "package_binding_schema": "trial-v5-package-v1",
            "preparer": {"path": str(TRIAL_ROOT / "prepare-trial-v5.py"), "sha256": _sha(TRIAL_ROOT / "prepare-trial-v5.py")},
            "prepared_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "identities": identities,
            "clone": clone,
            "assessment": assessment,
            "recipe": recipe,
            "build": {
                "network_scope": (
                    "docker build only: base image pull by pinned digest plus PyPI package "
                    "downloads during dependency sync inside the approved container builds; "
                    "no network at execution (sandbox runs use --network=none)"
                ),
                "dockerfiles": {
                    "baseline": str(TRIAL_ROOT / "docker" / "baseline.Dockerfile"),
                    "candidate": str(TRIAL_ROOT / "docker" / "candidate.Dockerfile"),
                },
                "base_image_pins": {
                    "python": BASE_IMAGE_PYTHON,
                    "validator": VALIDATOR_IMAGE,
                    "sandbox_dev_reference": SANDBOX_DEV_IMAGE,
                },
                "images": images,
            },
            "runner": {"path": str(TRIAL_ROOT / "run-trial-v5.py"), "sha256": runner_sha},
            "signing_script": {"path": str(SIGNING_SCRIPT)},
            "grant": {
                "expires_at_epoch": expires_epoch,
                "expires_at": expires_iso,
                "max_uses": 1,
                "one_use_per_phase": True,
                "order": "baseline run and record must complete before the candidate claim",
            },
            "requests": {
                phase: {
                    "request_sha256": data["sha256"],
                    "attempt_id": data["attempt_id"],
                    "environment_digest": data["environment_digest"],
                    "argv_sha256": data["argv_sha256"],
                    "image_ref": data["image_ref"],
                    "source_digest": data["source_digest"],
                    "nonce": data["body"]["nonce"],
                }
                for phase, data in requests.items()
            },
            "execution": {
                "engine_data_dir": str(ENGINE_DATA),
                "executor_root": str(EXEC_ROOT),
                "ledger": str(LEDGER),
                "oracle": str(ORACLE),
                "expectation_file": str(TRIAL_ROOT / "EXPECTED-CASES-V4.json"),
            },
            "verdict_policy": "NOT_PROVEN enforced by the engine record/compare; no upgrade claim",
        }
        for phase, data in requests.items():
            if hashlib.sha256(data["bytes"]).hexdigest() != data["sha256"]:
                raise PreparationError("request digest changed while staging")
            (approval_dir / f"{phase}.request.json").write_bytes(data["bytes"])
        manifest_path = approval_dir / "manifest.json"
        # Manifest first, then signer pins it; no self-referential signer hash.
        manifest_body = dumps(manifest)
        manifest_sha = hashlib.sha256(manifest_body).hexdigest()
        manifest_path.write_bytes(manifest_body)
        script = _signing_script(
            requests,
            manifest_path,
            TRIAL_ROOT / "run-trial-v5.py",
            expires_epoch,
            expires_iso,
            clone,
            recipe,
            images,
            manifest_sha,
        )
        SIGNING_SCRIPT.write_text(script)
        SIGNING_SCRIPT.chmod(0o755)
        summary = {
            "status": "PREPARED",
            "approval_directory": str(approval_dir),
            "manifest_sha256": manifest_sha,
            "runner_sha256": runner_sha,
            "signing_script": str(SIGNING_SCRIPT),
            "signing_script_sha256": _sha(SIGNING_SCRIPT),
            "expires_at": expires_iso,
            "baseline_request_sha256": requests["baseline"]["sha256"],
            "candidate_request_sha256": requests["candidate"]["sha256"],
            "baseline_image": images["baseline"]["ref"],
            "candidate_image": images["candidate"]["ref"],
            "baseline_versions": images["baseline"]["in_image_versions"],
            "candidate_versions": images["candidate"]["in_image_versions"],
            "owner_command": f"bash {SIGNING_SCRIPT}",
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    except Exception as error:  # noqa: BLE001
        suffix = f".ABANDONED-partial-unsigned-{started}"
        for path in created:
            try:
                if path.exists():
                    path.rename(path.with_name(path.name + suffix))
            except OSError:
                pass
        print(json.dumps({"status": "ABANDONED", "reason": str(error)[:400]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

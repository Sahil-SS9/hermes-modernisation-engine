#!/usr/bin/env python3
"""Run the trial-v5 lane under the owner-signed one-use grants.

Baseline first: the candidate claim is refused until baseline evidence has been
recorded from retained output bytes.  Every verdict stays NOT_PROVEN; this runner
adds no verdict of its own, it only classifies what the engine recorded.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TRIAL_ROOT = Path("/home/kensei/projects/modernisation-benchmarks/control/trial-v5")

_spec = importlib.util.spec_from_file_location(
    "trialv5_prepare", TRIAL_ROOT / "prepare-trial-v5.py"
)
prep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prep)

sys.path.insert(0, str(prep.ENGINE / "src"))
from hermes_modernisation import approvals, store  # noqa: E402
from hermes_modernisation import executor as executor_module  # noqa: E402
from hermes_modernisation.identity import snapshot  # noqa: E402
from hermes_modernisation.jsonio import dumps, loads  # noqa: E402

DEFAULT_SIGNATURES = "/home/sahil/trial-v5-signatures/trial-v5-signatures.txt"


class TrialError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _engine_cli(*args: str) -> dict:
    import os

    result = subprocess.run(
        [sys.executable, "-B", "-m", "hermes_modernisation", *args],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONPATH": str(prep.ENGINE / "src")},
    )
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    if result.returncode:
        raise TrialError(
            f"engine {args[1]} failed: {(result.stderr or payload.get('message', ''))[:400]}"
        )
    return payload


def _verify_approval(approval_dir: Path) -> dict:
    manifest_path = approval_dir / "manifest.json"
    if not manifest_path.is_file():
        raise TrialError("manifest.json missing from the approval directory")
    manifest = loads(manifest_path.read_bytes())
    if manifest.get("trial") != "trial-v5":
        raise TrialError("approval directory is not a trial-v5 grant set")
    if manifest.get("package_binding_schema") != "trial-v5-package-v1":
        raise TrialError("unsigned legacy package must be re-sealed before owner signing")
    execution = manifest.get("execution")
    expected_paths = {
        "engine_data_dir": prep.ENGINE_DATA,
        "executor_root": prep.EXEC_ROOT,
        "ledger": prep.LEDGER,
        "oracle": prep.ORACLE,
        "expectation_file": TRIAL_ROOT / "EXPECTED-CASES-V4.json",
    }
    if type(execution) is not dict or set(execution) != set(expected_paths):
        raise TrialError("unknown or missing execution fields in approval manifest")
    for name, expected in expected_paths.items():
        if execution[name] != str(expected):
            raise TrialError(f"approval {name} path differs from the fixed trial scope")
    expiry = manifest.get("grant", {}).get("expires_at_epoch")
    if type(expiry) is not int or expiry <= time.time():
        raise TrialError("approval package has expired")
    identities = manifest["identities"]
    for key, expected in (
        ("engine_commit", prep.ENGINE_COMMIT),
        ("engine_core_digest", prep.ENGINE_CORE_DIGEST),
        ("oracle_sha256", prep.ORACLE_SHA),
        ("expectation_sha256", prep.EXPECTATION_SHA),
        ("producer_sha256", prep.PRODUCER_SHA),
        ("recipe_digest", prep.RECIPE_DIGEST),
        ("enrolled_spki", prep.ENROLLED_SPKI),
    ):
        if identities.get(key) != expected:
            raise TrialError(f"manifest identity {key} does not match the pinned values")
    runner_path = Path(manifest["runner"]["path"])
    if _sha(runner_path) != manifest["runner"]["sha256"]:
        raise TrialError("runner program digest does not match the manifest")
    if runner_path != TRIAL_ROOT / "run-trial-v5.py":
        raise TrialError("unexpected runner path")
    preparer = manifest.get("preparer", {})
    if preparer.get("path") != str(TRIAL_ROOT / "prepare-trial-v5.py") or preparer.get("sha256") != _sha(TRIAL_ROOT / "prepare-trial-v5.py"):
        raise TrialError("preparer digest does not match the manifest")
    # No script-hash -> manifest-hash -> script-hash cycle: the static manifest
    # holds only its path. The owner's signed package binds the actual script.
    if manifest.get("signing_script") != {"path": str(TRIAL_ROOT / "sign-owner-trial-v5.sh")}:
        raise TrialError("unexpected signing script contract")
    if not (TRIAL_ROOT / "sign-owner-trial-v5.sh").is_file():
        raise TrialError("signing script missing")
    clone = Path(manifest["clone"]["path"])
    if _git(clone, "rev-parse", "HEAD") != prep.ORIGINAL_HEAD:
        raise TrialError("disposable clone HEAD is not the pinned baseline")
    if _git(clone, "status", "--porcelain"):
        raise TrialError("disposable clone is not clean")
    if snapshot(clone)["digest"] != manifest["clone"]["source_digest"]:
        raise TrialError("disposable clone identity changed since preparation")
    candidate = Path(manifest["recipe"]["root"])
    if snapshot(candidate)["digest"] != manifest["recipe"]["candidate_digest"]:
        raise TrialError("candidate root identity changed since preparation")
    for phase, data in manifest["requests"].items():
        request_path = approval_dir / f"{phase}.request.json"
        raw = request_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != data["request_sha256"]:
            raise TrialError(f"{phase} request digest mismatch")
        body = loads(raw)
        if body.get("expires_at") != expiry or body.get("operation", {}).get("job_id") != manifest["assessment"]["job_id"]:
            raise TrialError(f"{phase} grant expiry/job does not match the manifest")
        if body.get("nonce") != data["nonce"]:
            raise TrialError(f"{phase} grant nonce does not match the manifest")
        if approvals.canonical(body) != raw:
            raise TrialError(f"{phase} request is not canonical bytes")
        operation = body["operation"]
        if (
            body["max_uses"] != 1
            or operation["attempt_id"] != data["attempt_id"]
            or operation["environment_digest"] != data["environment_digest"]
            or operation["image_digest"] != data["image_ref"].split("@sha256:")[-1]
            or operation["source_digest"] != data["source_digest"]
            or hashlib.sha256(dumps({"argv": operation["argv"]})).hexdigest()
            != data["argv_sha256"]
            or operation["argv"][3] != _producer_program()
        ):
            raise TrialError(f"{phase} request contents mismatch the manifest")
    for phase, image in manifest["build"]["images"].items():
        inspected = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image["tag"]],
            capture_output=True,
            text=True,
        )
        digests = json.loads(inspected.stdout) if inspected.returncode == 0 else []
        if digests != [image["ref"]]:
            raise TrialError(f"{phase} image digest is no longer present as pinned")
    return manifest


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _producer_program() -> str:
    from hermes_modernisation import runner

    return runner.PROGRAM


def _package_payload(manifest: dict, manifest_sha: str) -> bytes:
    """Versioned owner-attested package bytes, independent of unsigned tags.

    The static manifest does not contain the signer digest (no hash cycle).
    The actual signer, preparer, runner, expectations and requests are all bound
    by this separate signature. It is verified before either grant is claimed.
    """
    approval_dir = Path(manifest["_approval_dir"])
    fields = [
        ("manifest_sha256", manifest_sha),
        ("runner_sha256", _sha(TRIAL_ROOT / "run-trial-v5.py")),
        ("preparer_sha256", _sha(TRIAL_ROOT / "prepare-trial-v5.py")),
        ("expectation_sha256", _sha(Path(manifest["execution"]["expectation_file"]))),
        ("signer_sha256", _sha(TRIAL_ROOT / "sign-owner-trial-v5.sh")),
        ("baseline_request_sha256", _sha(approval_dir / "baseline.request.json")),
        ("candidate_request_sha256", _sha(approval_dir / "candidate.request.json")),
        ("expires_at_epoch", str(manifest["grant"]["expires_at_epoch"])),
    ]
    return ("trial-v5-package-v1\n" + "".join(f"{key}={value}\n" for key, value in fields)).encode()


def _signatures(path: Path, manifest: dict, manifest_sha: str) -> dict:
    # This public signature file must never be a blocking pipe or an unbounded
    # input. The owner key is NOT read here: only its enrolled public half.
    import os
    import stat

    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 16384:
                raise TrialError("unsafe or oversized signature file")
            raw_file = os.read(fd, 16385)
            if len(raw_file) > 16384:
                raise TrialError("signature file exceeds its bound")
        finally:
            os.close(fd)
        text = raw_file.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise TrialError("signature file is unavailable or invalid") from error
    raw_lines = text.splitlines()
    if not raw_lines or raw_lines[0] != "trial-v5 signatures":
        raise TrialError("unknown signature file format")
    lines = {}
    for line in raw_lines[1:]:
        key, separator, value = line.partition("=")
        if not separator or key in lines:
            raise TrialError("malformed or duplicate signature field")
        lines[key] = value
    required = {"manifest_sha256", "runner_sha256", "expires_at_epoch", "baseline", "candidate",
                "package_payload_base64", "package_signature_base64"}
    if set(lines) != required:
        raise TrialError("owner-signed package attestation and both grants are required")
    try:
        expected = _package_payload(manifest, manifest_sha)
        payload = base64.b64decode(lines["package_payload_base64"], validate=True)
        package_signature = base64.b64decode(lines["package_signature_base64"], validate=True)
        if payload != expected or len(package_signature) != 64:
            raise TrialError("approval package changed after signing")
        public_key = prep.Ed25519PublicKey.from_public_bytes(prep._enrolled_public())
        public_key.verify(package_signature, payload)
        if (lines["manifest_sha256"] != manifest_sha
                or lines["runner_sha256"] != _sha(TRIAL_ROOT / "run-trial-v5.py")
                or lines["expires_at_epoch"] != str(manifest["grant"]["expires_at_epoch"])):
            raise TrialError("signature metadata does not match its signed package")
        if manifest["grant"]["expires_at_epoch"] <= time.time():
            raise TrialError("owner approval expired")
        # Verify BOTH request signatures before using the first one. A damaged
        # candidate signature must not burn an otherwise-valid baseline grant.
        for phase in ("baseline", "candidate"):
            signature = base64.b64decode(lines[phase], validate=True)
            body = (Path(manifest["_approval_dir"]) / f"{phase}.request.json").read_bytes()
            if len(signature) != 64:
                raise TrialError(f"{phase} signature is not an Ed25519 signature")
            public_key.verify(signature, body)
    except TrialError:
        raise
    except Exception as error:
        raise TrialError("unenrolled owner or invalid package/request signature") from error
    return {phase: lines[phase] for phase in ("baseline", "candidate")}


def _run_phase(manifest: dict, phase: str, signature: str, authority) -> dict:
    data = manifest["requests"][phase]
    approval_dir = Path(manifest["_approval_dir"])
    raw = (approval_dir / f"{phase}.request.json").read_bytes()
    body = loads(raw)
    operation = body["operation"]
    grant = {"body": body, "signature": signature}
    source = Path(manifest["clone"]["path"]) if phase == "baseline" else Path(manifest["recipe"]["root"])
    manager = executor_module.Executor(
        authority,
        Path(manifest["execution"]["executor_root"]),
        data["image_ref"],
        profile="default",
        phase=phase,
    )
    receipt = manager.run(grant, operation, source, Path(manifest["execution"]["oracle"]))
    attempt = Path(manifest["execution"]["executor_root"]) / operation["attempt_id"]
    output_path = attempt / "output.bin"
    if (
        receipt["process_exit_code"] != 0
        or receipt["timed_out"]
        or receipt["truncated"]
        or not receipt["container_removed"]
        or not receipt["source_unchanged"]
    ):
        raise TrialError(f"{phase} run did not collect cleanly: {json.dumps({k: receipt[k] for k in ('process_exit_code','timed_out','truncated','container_removed','source_unchanged')})}")
    if hashlib.sha256(output_path.read_bytes()).hexdigest() != receipt["output_sha256"]:
        raise TrialError(f"{phase} retained output does not match the receipt")
    record = _engine_cli(
        "--data-dir",
        manifest["execution"]["engine_data_dir"],
        "record",
        "--job",
        manifest["assessment"]["job_id"],
        "--phase",
        phase,
        "--source-digest",
        data["source_digest"],
        "--expectation",
        Path(manifest["execution"]["expectation_file"]).read_text(),
        "--output",
        str(output_path),
    )
    if not record.get("accepted"):
        raise TrialError(f"{phase} retained output was not accepted by the engine evaluator")
    return {"receipt": receipt, "record": record, "attempt": str(attempt), "output": str(output_path)}


def _extract_junit(output_path: Path, destination: Path) -> None:
    text = output_path.read_text(errors="replace")
    lines = text.splitlines()
    begins = [i for i, line in enumerate(lines) if line == "RUNNER_JUNIT_BEGIN"]
    ends = [i for i, line in enumerate(lines) if line == "RUNNER_JUNIT_END"]
    if len(begins) != 1 or len(ends) != 1 or ends[0] != begins[0] + 2:
        raise TrialError("retained output has no single JUnit block")
    declared = [line for line in lines if line.startswith("RUNNER_JUNIT_SHA256=")]
    sizes = [line for line in lines if line.startswith("RUNNER_JUNIT_BYTES=")]
    if len(declared) != 1 or len(sizes) != 1:
        raise TrialError("retained output has no single JUnit seal")
    junit = base64.b64decode(lines[begins[0] + 1], validate=True)
    if hashlib.sha256(junit).hexdigest() != declared[0].split("=", 1)[1]:
        raise TrialError("retained JUnit bytes do not match the sealed digest")
    if len(junit) != int(sizes[0].split("=", 1)[1]):
        raise TrialError("retained JUnit bytes do not match the sealed length")
    destination.write_bytes(junit)


def _classify_warnings(rows: dict) -> dict:
    def classify(line: str) -> str:
        if "site-packages" in line or re.search(r"\b(fastapi|starlette|pydantic|anyio|httpx|pytest|pluggy|uvicorn)\b", line):
            return "third-party"
        if line.strip().startswith("tests/") or re.search(r"\btests/[A-Za-z0-9_/.\-]+\.py:\d+", line):
            return "app"
        return "unclassified"

    out = {}
    for phase, evaluation in rows.items():
        lines = evaluation.get("warning_lines") or []
        out[phase] = {
            "count": evaluation.get("warnings_count", 0),
            "classified": [
                {"line": line, "class": classify(line)} for line in lines
            ],
        }
    baseline = {item["line"] for item in out["baseline"]["classified"]}
    candidate = {item["line"] for item in out["candidate"]["classified"]}
    deltas = {
        "added": sorted(candidate - baseline),
        "removed": sorted(baseline - candidate),
        "added_by_class": {
            cls: sorted(
                item["line"]
                for item in out["candidate"]["classified"]
                if item["line"] not in baseline and item["class"] == cls
            )
            for cls in ("app", "third-party", "unclassified")
        },
    }
    return {"per_phase": out, "deltas": deltas}


def _lock_versions(path: Path) -> dict:
    text = path.read_text()
    found = {}
    for name in ("pytest", "pytest-asyncio", "fastapi", "starlette", "httpx"):
        match = re.search(
            rf'name = "{re.escape(name)}"\nversion = "([^"]+)"', text
        )
        if match:
            found[name] = match.group(1)
    return found


def _version_tuple(value: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def _cross_check(manifest: dict) -> dict:
    baseline_lock = _lock_versions(Path(manifest["clone"]["path"]) / "uv.lock")
    candidate_lock = _lock_versions(Path(manifest["recipe"]["root"]) / "uv.lock")
    notes = [
        "baseline image versions are runtime witnesses of the container build, not repo state; "
        "repo state is the pinned uv.lock files compared here",
    ]
    downgrades = []
    for name, before in baseline_lock.items():
        after = candidate_lock.get(name)
        if after is not None and _version_tuple(after) < _version_tuple(before):
            downgrades.append({"package": name, "baseline": before, "candidate": after})
    if downgrades:
        notes.append("downgrade detected in the lock comparison; flagged, not accepted")
    else:
        notes.append("no package downgrade between baseline and candidate locks")
    return {
        "baseline_lock_versions": baseline_lock,
        "candidate_lock_versions": candidate_lock,
        "baseline_image_versions": manifest["build"]["images"]["baseline"]["in_image_versions"],
        "candidate_image_versions": manifest["build"]["images"]["candidate"]["in_image_versions"],
        "downgrades": downgrades,
        "notes": notes,
    }


def _containers_clean(manifest: dict) -> dict:
    ours = [
        "modernise-"
        + hashlib.sha256(data["attempt_id"].encode()).hexdigest()[:32]
        for data in manifest["requests"].values()
    ]
    listed = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=modernise-", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    remaining = [name for name in listed.stdout.split() if name]
    return {
        "attempt_container_names": ours,
        "our_containers_remaining": [name for name in remaining if name in ours],
        "other_modernise_containers": [name for name in remaining if name not in ours],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approval_dir", type=Path)
    parser.add_argument("--signatures", default=DEFAULT_SIGNATURES)
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="verify every gate without touching signatures or claiming anything",
    )
    args = parser.parse_args(argv)
    started = time.time_ns()
    prep._verify_identities()
    manifest = _verify_approval(args.approval_dir)
    manifest["_approval_dir"] = str(args.approval_dir)
    manifest_sha = _sha(args.approval_dir / "manifest.json")
    expectation_raw = Path(manifest["execution"]["expectation_file"]).read_bytes()
    if hashlib.sha256(expectation_raw).hexdigest() != prep.EXPECTATION_SHA:
        raise TrialError("expectation file digest mismatch")
    if args.preflight:
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT PASS",
                    "approval_directory": str(args.approval_dir),
                    "manifest_sha256": manifest_sha,
                    "runner_sha256": _sha(TRIAL_ROOT / "run-trial-v5.py"),
                    "phases": ["baseline", "candidate"],
                    "order_gate": "candidate claim refused until baseline evidence is recorded",
                    "grant_expiry": manifest["grant"]["expires_at"],
                    "verdict_policy": manifest["verdict_policy"],
                    "execution_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    signatures = _signatures(Path(args.signatures), manifest, manifest_sha)
    authority = approvals.ExternalAuthority(
        {prep.ACTOR: prep._enrolled_public()}, Path(manifest["execution"]["ledger"])
    )
    baseline = _run_phase(manifest, "baseline", signatures["baseline"], authority)
    rows = {row["phase"]: row for row in store.Store(Path(manifest["execution"]["engine_data_dir"])).evidence_for(manifest["assessment"]["job_id"])}
    if "baseline" not in rows or not rows["baseline"]["evaluation"].get("accepted"):
        raise TrialError("order gate: baseline evidence was not recorded; candidate run refused")
    candidate = _run_phase(manifest, "candidate", signatures["candidate"], authority)
    # The earlier snapshot served only the baseline order gate. Re-read after
    # candidate recording before comparison/export; never package stale rows.
    rows = {row["phase"]: row for row in store.Store(
        Path(manifest["execution"]["engine_data_dir"])
    ).evidence_for(manifest["assessment"]["job_id"])}
    if set(rows) != {"baseline", "candidate"} or any(
        row["evaluation"].get("accepted") is not True for row in rows.values()
    ):
        raise TrialError("both accepted phases are required before evidence export")
    comparison = _engine_cli(
        "--data-dir",
        manifest["execution"]["engine_data_dir"],
        "compare",
        "--job",
        manifest["assessment"]["job_id"],
    )
    refusal_proof = None
    try:
        baseline_body = loads((args.approval_dir / "baseline.request.json").read_bytes())
        authority.claim(
            {"body": baseline_body, "signature": signatures["baseline"]},
            baseline_body["operation"],
        )
        raise TrialError("replay refusal proof failed: a consumed grant was accepted")
    except approvals.AuthorityDenied as denial:
        refusal_proof = {"refused": True, "reason": str(denial)}
    evidence_dir = Path(manifest["execution"]["executor_root"]) / f"trial-v5-evidence-{started}"
    evidence_dir.mkdir(parents=True, mode=0o700)
    copies = {
        "manifest.json": (args.approval_dir / "manifest.json").read_bytes(),
        "baseline-receipt.json": dumps(baseline["receipt"]),
        "candidate-receipt.json": dumps(candidate["receipt"]),
        "baseline-record.json": dumps(baseline["record"]),
        "candidate-record.json": dumps(candidate["record"]),
        "baseline-evaluation.json": dumps(rows["baseline"]["evaluation"]),
        "candidate-evaluation.json": dumps(rows["candidate"]["evaluation"]),
        "comparison.json": dumps(comparison),
        "replay-refusal-proof.json": dumps(refusal_proof),
        "warning-classification.json": dumps(
            _classify_warnings(
                {
                    "baseline": rows["baseline"]["evaluation"],
                    "candidate": rows["candidate"]["evaluation"],
                }
            )
        ),
        "lock-cross-check.json": dumps(_cross_check(manifest)),
        "container-cleanup.json": dumps(_containers_clean(manifest)),
    }
    _extract_junit(Path(baseline["output"]), evidence_dir / "baseline-junit.xml")
    _extract_junit(Path(candidate["output"]), evidence_dir / "candidate-junit.xml")
    for name, body in copies.items():
        (evidence_dir / name).write_bytes(body.encode() if isinstance(body, str) else body)
    names = sorted(
        p.name for p in evidence_dir.iterdir() if p.is_file() and p.name != "SHA256SUMS"
    )
    sums = "\n".join(
        f"{hashlib.sha256((evidence_dir / name).read_bytes()).hexdigest()}  {name}"
        for name in names
    )
    (evidence_dir / "SHA256SUMS").write_text(sums + "\n")
    handback = args.approval_dir / "evidence"
    handback.mkdir(parents=True, mode=0o755)
    for path in sorted(evidence_dir.iterdir()):
        if path.is_file():
            target = handback / path.name
            target.write_bytes(path.read_bytes())
            target.chmod(0o644)
    result_text = (
        "MODERNISATION TRIAL v5 - RESULT (engine-in-the-loop, first real-project run "
        "through the engine's own producer/record/compare chain)\n\n"
        f"VERDICT: {comparison['verdict']} (engine compare inner verdict: "
        f"{comparison.get('comparison', {}).get('verdict', 'n/a')}); proof stays NOT_PROVEN "
        "by engine policy - process-only receipts, selected-scope regression, "
        "candidate-authored case results.\n"
        f"Baseline attempt: {baseline['attempt']} (exit 0, retained output "
        f"{baseline['receipt']['output_bytes']} bytes, accepted from retained bytes)\n"
        f"Candidate attempt: {candidate['attempt']} (exit 0, retained output "
        f"{candidate['receipt']['output_bytes']} bytes)\n"
        f"Cases compared: {comparison.get('compared_cases', 0)} of 20; identical set "
        f"required by the zero-skip expectation.\n"
        f"Replay refusal proof: {json.dumps(refusal_proof)}\n"
        f"Containers: {json.dumps(_containers_clean(manifest))}\n"
        f"Evidence: {evidence_dir} (SHA256SUMS) and owner-readable copy {handback}\n"
    )
    result_path = TRIAL_ROOT / f"RESULT-trial-v5-{datetime.now(timezone.utc).strftime('%Y%m%d')}.txt"
    result_path.write_text(result_text)
    result_path.chmod(0o644)
    print(json.dumps({"status": "TRIAL COMPLETE", "evidence": str(evidence_dir), "handback": str(handback), "result": str(result_path), "verdict": comparison["verdict"], "inner": comparison.get("comparison", {}).get("verdict")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TrialError, approvals.AuthorityDenied) as error:
        print(json.dumps({"status": "REFUSED", "reason": str(error)[:500]}), file=sys.stderr)
        raise SystemExit(1)

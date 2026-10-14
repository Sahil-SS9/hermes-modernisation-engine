"""Read-only Phase 0 discovery; never load plugins or execute benchmark sources.

This is an engineering spike, not the Modernisation Engine implementation.
Source inspection cannot certify authentic CLI/gateway approvals or OS isolation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HOST_PIN = "0e427d788d253630d38a3a51cd76849e73cd6925"
BENCHMARK_PIN = "bdbc72300bb494a393992bf4b49259c06811c2b9"


def command(argv: list[str], cwd: str | None = None) -> dict:
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=30)
        return {"argv": argv, "cwd": cwd, "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"argv": argv, "cwd": cwd, "exit_code": None, "error": str(error)}


def git(repo: str, *args: str) -> dict:
    return command(["git", "--no-optional-locks", "-C", repo, *args])


def source(repo: str, path: str) -> tuple[str, dict]:
    result = git(repo, "show", f"{HOST_PIN}:{path}")
    if result["exit_code"] != 0:
        raise RuntimeError(f"Pinned source unavailable: {path}: {result}")
    text = result["stdout"]
    return text, {"path": path, "git_pin": HOST_PIN,
                  "sha256": hashlib.sha256(text.encode()).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-repo", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--original", required=True)
    args = parser.parse_args()
    sdk, sdk_identity = source(args.host_repo, "hermes_cli/plugins.py")
    context = next(node for node in ast.parse(sdk).body
                   if isinstance(node, ast.ClassDef) and node.name == "PluginContext")
    methods = {node.name: node for node in context.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    transport, transport_identity = source(args.host_repo, "hermes_cli/approval_transport.py")
    registry, registry_identity = source(args.host_repo, "tools/registry.py")
    report = {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PHASE_0",
        "sources": [sdk_identity, transport_identity, registry_identity],
        "source_observations": {
            "public_context_methods": sorted(name for name in methods if not name.startswith("_")),
            "approval_transport_registration": ast.get_source_segment(sdk, methods["register_approval_transport"]),
            "registry_dispatch": ast.get_source_segment(sdk, methods["dispatch_tool"]),
            "transport_public_definitions": [node.name for node in ast.parse(transport).body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_")],
        },
        "benchmark": {"path": str(Path(args.benchmark).resolve()),
                      "expected_base": BENCHMARK_PIN,
                      "head": git(args.benchmark, "rev-parse", "HEAD"),
                      "status": git(args.benchmark, "status", "--short", "--branch"),
                      "remotes": git(args.benchmark, "remote", "-v"),
                      "push_default": git(args.benchmark, "config", "--get", "push.default")},
        "original": {"path": args.original,
                     "head": git(args.original, "rev-parse", "HEAD"),
                     "status": git(args.original, "status", "--short", "--branch")},
        "prerequisite_probes": {},
        "limits": [
            "No real plugin installation, loader, CLI, slash, agent or gateway smoke test performed.",
            "No benchmark code, build hook, test suite or model call executed.",
            "Source inspection is not runtime proof or proof that every possible host API is absent.",
            "Docker info is discovery only; no container started and no isolation backend certified.",
            "No licences or reference comparator conformance certified in this spike.",
        ],
        "blockers": [
            "M0.2: No demonstrated public request/grant/executor route binding authentic owner permission to the full operation contract.",
            "M0.3: No validated isolation backend; Bubblewrap probe must be read literally; Docker remains a candidate needing owner approval and adversarial tests.",
        ],
    }
    if shutil.which("bwrap"):
        report["prerequisite_probes"]["bubblewrap"] = command([
            "bwrap", "--unshare-all", "--die-with-parent", "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "/usr/bin/true"])
    else:
        report["prerequisite_probes"]["bubblewrap"] = {"available": False}
    if shutil.which("docker"):
        report["prerequisite_probes"]["docker"] = command([
            "docker", "info", "--format", "{{json .SecurityOptions}}"])
    else:
        report["prerequisite_probes"]["docker"] = {"available": False}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 2  # Discovery blockers; never export a green release gate.


if __name__ == "__main__":
    raise SystemExit(main())

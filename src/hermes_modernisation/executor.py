"""External operator executor primitive, never a model-callable tool.

Only an authentic, exact, one-use grant permits create/start. Receipts attest
process collection only; they cannot establish test adequacy or equivalence.
Native run/resume stay disabled until complete executor acceptance.
"""

import hashlib
import json
import os
import re
import selectors
import subprocess
import time
from pathlib import Path
from .approvals import AuthorityDenied, ExternalAuthority, validate_operation
from .identity import snapshot, read_source
from .jsonio import ContractError, dumps, loads
from .sandbox import SandboxSpec, docker_argv
from .store import identifier


class Executor:
    def __init__(
        self,
        authority: ExternalAuthority,
        root: Path,
        image: str,
        *,
        profile="default",
        phase="candidate",
    ):
        if phase not in ("baseline", "candidate"):
            raise ContractError("Unsupported execution phase")
        self.authority = authority
        self.root = Path(root)
        self.image = image
        self.profile = identifier(profile)
        self.phase = phase

    def environment(self, operation):
        return {
            "schema_version": 1,
            "image": self.image,
            "argv": operation["argv"],
            "oracle_digest": operation["oracle_digest"],
            "network": "none",
            "readonly_source": True,
            "collector": "bounded-process-v1",
            "source_identity": "files-and-dirs-v2",
            "phase": self.phase,
            "engine_core_digest": snapshot(Path(__file__).parent)["digest"],
        }

    def prepare(self, operation, source, oracle):
        validate_operation(operation)
        if operation.get("profile") != self.profile:
            raise ContractError("Execution profile mismatch")
        if operation.get("image_digest") != self.image.split("@sha256:")[-1]:
            raise ContractError("Image does not match trusted executor configuration")
        source = Path(source)
        oracle = Path(oracle)
        if oracle.is_symlink() or not oracle.is_file():
            raise ContractError("Independent oracle descriptor required")
        with oracle.open("rb") as stream:
            raw = stream.read(1048577)
        if len(raw) > 1048576 or hashlib.sha256(raw).hexdigest() != operation.get(
            "oracle_digest"
        ):
            raise ContractError("Oracle descriptor changed")
        identity = snapshot(source)
        if (
            identity["digest"] != operation.get("source_digest")
            or operation.get("candidate_digest") != identity["digest"]
        ):
            raise ContractError("Source identity changed")
        if self.root.resolve().is_relative_to(
            source.resolve()
        ) or source.resolve().is_relative_to(self.root.resolve()):
            raise ContractError("Executor storage must not overlap source")
        identifier(operation.get("attempt_id"))
        # Validate every launch policy before any authority claim or execution.
        docker_argv(
            SandboxSpec(
                self.image, source, tuple(operation.get("argv", [])), "modernise-check"
            )
        )
        env = self.environment(operation)
        if hashlib.sha256(dumps(env)).hexdigest() != operation.get(
            "environment_digest"
        ):
            raise ContractError("Environment contract changed")
        return identity

    def run(self, grant, operation, source, oracle):
        operation = loads(dumps(operation))
        grant = loads(dumps(grant))
        identity = self.prepare(operation, source, oracle)
        # All runtime/platform checks occur before claim; no source code runs here.
        security = subprocess.run(
            ["docker", "info", "--format", "{{json .SecurityOptions}}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if security.returncode or "name=rootless" not in json.loads(security.stdout):
            raise ContractError("Rootless runtime not verified")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.resolve() != self.root or self.root.stat().st_mode & 0o077:
            raise ContractError("Executor root must be private and unambiguous")
        attempt = self.root / operation["attempt_id"]
        attempt.mkdir(mode=0o700)
        frozen = attempt / "source"
        frozen.mkdir(mode=0o755)
        for record in identity["directories"]:
            (frozen / record["path"]).mkdir(parents=True, exist_ok=True, mode=0o755)
        for record in identity["files"]:
            raw, mode = read_source(source, record["path"])
            if hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ContractError("Source changed while freezing")
            target = frozen / record["path"]
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            with target.open("xb") as stream:
                stream.write(raw)
            target.chmod(mode)
        for record in sorted(
            identity["directories"],
            key=lambda record: record["path"].count("/"),
            reverse=True,
        ):
            (frozen / record["path"]).chmod(record["mode"])
        if (
            snapshot(frozen)["digest"] != identity["digest"]
            or snapshot(source)["digest"] != identity["digest"]
        ):
            raise ContractError("Frozen snapshot mismatch")
        name = (
            "modernise-"
            + hashlib.sha256(operation["attempt_id"].encode()).hexdigest()[:32]
        )
        args = docker_argv(
            SandboxSpec(self.image, frozen, tuple(operation["argv"]), name)
        )
        create = (
            [
                "docker",
                "create",
                "--init",
                "--attach",
                "stdout",
                "--attach",
                "stderr",
            ]
            + args[3:]
        )  # Strip only the fixed Docker run/--rm prefix, never signed payload arguments.
        nonce = self.authority.claim(grant, operation)
        self._write(
            attempt / "attempt.json",
            {
                "operation": operation,
                "authority_nonce": nonce,
                "container_name": name,
                "state": "CLAIMED",
            },
        )
        started = time.monotonic()
        container = None
        receipt = None
        try:
            created = subprocess.run(create, capture_output=True, text=True, timeout=15)
            if created.returncode:
                raise ContractError("Container create failed: " + created.stderr[:2000])
            candidate_id = created.stdout.strip()
            if not re.fullmatch("[a-f0-9]{64}", candidate_id):
                raise ContractError("Runtime returned invalid container identity")
            container = candidate_id
            self._write(
                attempt / "container.json", {"container_id": container, "name": name}
            )
            if time.time() >= grant["body"]["expires_at"]:
                raise AuthorityDenied("Grant expired before start")
            output, timed_out, truncated = self._collect(
                container, operation["timeout_seconds"], operation["output_limit_bytes"]
            )
            if timed_out or truncated:
                subprocess.run(
                    ["docker", "kill", container], capture_output=True, timeout=15
                )
            state = subprocess.run(
                ["docker", "inspect", "--format", "{{json .State}}", container],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if state.returncode:
                raise ContractError("Runtime process state unavailable")
            state = json.loads(state.stdout)
            if state["Running"] or state.get("Status") != "exited":
                raise ContractError("Container did not reach a collected exited state")
            self._write_bytes(attempt / "output.bin", output)
            receipt = {
                "schema_version": 1,
                "grade": "observed-process-only",
                "actor": operation["actor"],
                "profile": self.profile,
                "job_id": operation["job_id"],
                "attempt_id": operation["attempt_id"],
                "phase": self.phase,
                "source_digest": identity["digest"],
                "oracle_digest": operation["oracle_digest"],
                "environment_digest": operation["environment_digest"],
                "image": self.image,
                "authority_nonce": nonce,
                "process_exit_code": state["ExitCode"],
                "timed_out": timed_out,
                "truncated": truncated,
                "output_bytes": len(output),
                "output_sha256": hashlib.sha256(output).hexdigest(),
                "duration_seconds": round(time.monotonic() - started, 6),
                "container_removed": False,
                "source_unchanged": snapshot(source)["digest"] == identity["digest"],
                "verdict": "NOT_PROVEN",
                "missing_evidence": [
                    "protected external case evaluation and authenticated receipt acceptance",
                    "rule adequacy and mutation controls",
                ],
            }
        finally:
            target = container or name
            subprocess.run(
                ["docker", "rm", "-f", target],
                capture_output=True,
                text=True,
                timeout=15,
            )
            inspect = subprocess.run(
                ["docker", "container", "inspect", target],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if inspect.returncode == 0 or "No such" not in inspect.stderr:
                raise ContractError(
                    "Container cleanup unverified; quarantine attempt, no resume"
                )
            if receipt is not None:
                receipt["container_removed"] = True
                self._write(attempt / "receipt.json", receipt)
        return receipt

    @staticmethod
    def _write(path, value):
        Executor._write_bytes(path, dumps(value))

    @staticmethod
    def _write_bytes(path, raw):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _collect(container, timeout, limit):
        process = subprocess.Popen(
            ["docker", "start", "-a", container],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        data = bytearray()
        deadline = time.monotonic() + timeout
        timed_out = False
        truncated = False
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        break
                    for key, _ in selector.select(min(remaining, 0.2)):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        available = limit - len(data)
                        data.extend(chunk[:available])
                        if len(chunk) > available:
                            truncated = True
                            break
                    if truncated:
                        break
            if not (timed_out or truncated):
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
        return bytes(data), timed_out, truncated

"""Executor regressions use simulated runtime boundaries, never real owner keys."""

import hashlib
from types import SimpleNamespace
import pytest
from hermes_modernisation.approvals import AuthorityDenied
from hermes_modernisation.executor import Executor
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError, dumps

IMAGE = "fixture@sha256:" + "a" * 64


class DenyingAuthority:
    def claim(self, grant, operation):
        raise AuthorityDenied("Fixture is deliberately unsigned")


def setup(tmp_path):
    source = tmp_path / "repo"
    source.mkdir()
    (source / "a.py").write_text("print(1)")
    oracle = tmp_path / "oracle.json"
    oracle.write_bytes(b'{"cases":[1]}')
    executor = Executor(DenyingAuthority(), tmp_path / "external", IMAGE)
    operation = {
        "schema_version": 1,
        "actor": "fixture",
        "profile": "default",
        "job_id": "job",
        "attempt_id": "one",
        "source_digest": snapshot(source)["digest"],
        "candidate_digest": snapshot(source)["digest"],
        "oracle_digest": hashlib.sha256(oracle.read_bytes()).hexdigest(),
        "image_digest": "a" * 64,
        "argv": ["python", "a.py"],
        "read_roots": ["/source"],
        "write_roots": ["/tmp", "/work"],
        "network": "none",
        "timeout_seconds": 1,
        "output_limit_bytes": 1024,
    }
    env = executor.environment(operation)
    operation["environment_digest"] = hashlib.sha256(dumps(env)).hexdigest()
    return executor, operation, source, oracle


def test_unsigned_request_can_never_create_or_start(tmp_path, monkeypatch):
    e, op, source, oracle = setup(tmp_path)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        assert argv[:2] == ["docker", "info"], "Unauthorised runtime action"
        return SimpleNamespace(returncode=0, stdout='["name=rootless"]')

    monkeypatch.setattr("subprocess.run", run)
    with pytest.raises(AuthorityDenied):
        e.run({}, op, source, oracle)
    assert len(calls) == 1


def test_source_and_oracle_changes_deny_before_runtime_query(tmp_path, monkeypatch):
    e, op, source, oracle = setup(tmp_path)

    def bomb(*args, **kwargs):
        raise AssertionError("Runtime touched before identity validation")

    monkeypatch.setattr("subprocess.run", bomb)
    (source / "a.py").write_text("changed")
    with pytest.raises(ContractError):
        e.run({}, op, source, oracle)
    oracle.write_bytes(b"changed")
    with pytest.raises(ContractError):
        e.prepare(op, source, oracle)


def test_large_output_is_not_serialised_as_one_json_contract(tmp_path):
    raw = b"x" * 4194304
    Executor._write_bytes(tmp_path / "output.bin", raw)
    assert (tmp_path / "output.bin").read_bytes() == raw
    with pytest.raises(FileExistsError):
        Executor._write_bytes(tmp_path / "output.bin", b"overwritten")


def test_empty_directories_are_frozen_and_bound(tmp_path, monkeypatch):
    e, op, source, oracle = setup(tmp_path)
    before = op["source_digest"]
    (source / "empty").mkdir()
    assert snapshot(source)["digest"] != before


@pytest.mark.parametrize("returned_id", ["c" * 64, "--all"])
def test_simulated_runtime_receipt_and_safe_cleanup_with_real_fixture_signature(
    tmp_path, monkeypatch, returned_id
):
    import base64
    import json
    import time
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from hermes_modernisation.approvals import ExternalAuthority

    e, op, source, oracle = setup(tmp_path)
    op["argv"].append("--rm")
    op["environment_digest"] = hashlib.sha256(dumps(e.environment(op))).hexdigest()
    key = Ed25519PrivateKey.generate()
    e.authority = ExternalAuthority(
        {"fixture": key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)},
        tmp_path / "claims.sqlite",
    )
    now = int(time.time())
    body = {
        "schema_version": 1,
        "expires_at": now + 60,
        "nonce": "fixture-nonce-one",
        "max_uses": 1,
        "operation": op,
    }
    grant = {
        "body": body,
        "signature": base64.b64encode(key.sign(dumps(body))).decode(),
    }
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ["docker", "info"]:
            return SimpleNamespace(returncode=0, stdout='["name=rootless"]')
        if argv[:2] == ["docker", "create"]:
            assert argv[-len(op["argv"]) :] == op["argv"], (
                "Signed command argv was altered"
            )
            return SimpleNamespace(returncode=0, stdout=returned_id)
        if argv[:2] == ["docker", "inspect"]:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {"Running": False, "Status": "exited", "ExitCode": 0}
                ),
            )
        if argv[:3] == ["docker", "rm", "-f"]:
            return SimpleNamespace(returncode=0, stdout="")
        if argv[:3] == ["docker", "container", "inspect"]:
            return SimpleNamespace(returncode=1, stderr="No such container")
        raise AssertionError(argv)

    monkeypatch.setattr("subprocess.run", run)
    monkeypatch.setattr(
        Executor,
        "_collect",
        staticmethod(lambda *args: (b"3 tests passed\n", False, False)),
    )
    if returned_id.startswith("--"):
        with pytest.raises(ContractError):
            e.run(grant, op, source, oracle)
    else:
        receipt = e.run(grant, op, source, oracle)
        assert (
            receipt["grade"] == "observed-process-only"
            and receipt["verdict"] == "NOT_PROVEN"
        )
        assert receipt["container_removed"] and receipt["source_unchanged"]
        assert "tests_passed" not in receipt
        with pytest.raises(AuthorityDenied):
            e.authority.claim(grant, op)
    cleanup = [argv for argv in calls if argv[:3] == ["docker", "rm", "-f"]]
    assert len(cleanup) == 1 and not cleanup[0][-1].startswith("--")


def test_protected_input_bytes_are_bound_by_the_signed_environment(tmp_path):
    e, op, _, _ = setup(tmp_path)
    e.input_data = b'{"cases":[{"input":7}]}'
    env = e.environment(op)
    assert env.get("input_sha256") == hashlib.sha256(e.input_data).hexdigest()
    assert env["collector"] == "bounded-json-response-v1"

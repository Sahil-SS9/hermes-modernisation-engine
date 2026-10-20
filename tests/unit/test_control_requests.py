"""Public owner control requests cannot mint authority or replay lost work."""

import base64
import hashlib
import time
import uuid

import pytest

from hermes_modernisation.approvals import canonical
from hermes_modernisation.jsonio import ContractError, dumps
from test_review_requests import configured_fixture


def control_fixture(tmp_path):
    engine, job, contract, key, workspace, config = configured_fixture(tmp_path)
    attempt = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "control_fixture", "timeout_seconds": 20, "output_limit_bytes": 65536})
    return engine, job, attempt, key, workspace


def sign(key, decision):
    body = {"schema_version": 1, "decision": decision, "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
    return {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}


def test_control_request_is_read_only_and_binds_exact_attempt_not_arbitrary_container(tmp_path, monkeypatch):
    engine, job, attempt, _, _ = control_fixture(tmp_path)
    before = (engine.store.root / "jobs.sqlite").read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Unsigned owner control requests must not touch Docker")

    monkeypatch.setattr("subprocess.run", forbidden)
    result = engine.invoke("control_request", {"job": job["job_id"], "attempt": attempt["attempt_id"], "actor": "fixture_owner", "purpose": "recover"})
    decision = result["decision"]
    assert result["permission_granted"] is False and result["execution_performed"] is False
    assert decision["kind"] == "ControlDecision" and decision["attempt_id"] == attempt["attempt_id"]
    assert decision["operation_digest"] == hashlib.sha256(dumps(attempt["operation"])).hexdigest()
    assert decision["container_name"] == "modernise-" + hashlib.sha256(attempt["attempt_id"].encode()).hexdigest()[:32]
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


@pytest.mark.parametrize("action", ["cancel", "recover"])
def test_unsigned_control_refuses_before_job_or_runtime_changes(tmp_path, monkeypatch, action):
    engine, job, attempt, _, _ = control_fixture(tmp_path)
    before = (engine.store.root / "jobs.sqlite").read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("A model's cancel/recover text is not owner authority")

    monkeypatch.setattr("subprocess.run", forbidden)
    with pytest.raises((ContractError, PermissionError), match="signed|grant|authority|decision"):
        engine.invoke(action, {"job": job["job_id"], "attempt": attempt["attempt_id"], "grant": {"approved": True}})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


def test_signed_cancel_requests_cooperative_stop_without_stealing_the_live_worker(tmp_path, monkeypatch):
    engine, job, attempt, key, _ = control_fixture(tmp_path)
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker")
    draft = engine.invoke("control_request", {"job": job["job_id"], "attempt": attempt["attempt_id"], "actor": "fixture_owner", "purpose": "cancel"})

    def forbidden(*args, **kwargs):
        raise AssertionError("Cancellation request must not race the worker's create/start")

    monkeypatch.setattr("subprocess.run", forbidden)
    result = engine.invoke("cancel", {"job": job["job_id"], "attempt": attempt["attempt_id"], "grant": sign(key, draft["decision"])})
    assert result["cancel_requested"] is True
    assert engine.store.get(job["job_id"])["cancel_ref"]["attempt_id"] == attempt["attempt_id"]
    # Requesting cancellation does not hand a second worker authority/ownership.
    engine.store.stop_attempt(job["job_id"], attempt["attempt_id"], lease, "CANCELLED", "Cooperative worker acknowledged owner stop")
    assert engine.store.attempts_for(job["job_id"])[0]["state"] == "CANCELLED"


@pytest.mark.parametrize("source_changed", [False, True])
def test_signed_recovery_retires_only_exact_runtime_without_adopting_old_output(tmp_path, monkeypatch, source_changed):
    import json
    import subprocess

    engine, job, attempt, key, _ = control_fixture(tmp_path)
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "lost_worker", now=100, lease_seconds=1)
    decision = engine.invoke("control_request", {"job": job["job_id"], "attempt": attempt["attempt_id"], "actor": "fixture_owner", "purpose": "recover"})["decision"]
    if source_changed:
        (tmp_path / "legacy" / "app.py").write_text("raise RuntimeError('changed source')\n")
    calls = []
    existing = [True]
    # Runtime metadata is a declared stub, not proof of a real Docker process.
    runtime_image = "modernise-validator-fixed@sha256:" + attempt["operation"]["image_digest"]

    def docker(argv, **kwargs):
        calls.append(argv)
        if argv[1] == "info":
            return subprocess.CompletedProcess(argv, 0, json.dumps(["name=rootless"]), "")
        if argv[1:3] == ["container", "inspect"]:
            assert argv[-1] == decision["container_name"]
            if existing[0]:
                return subprocess.CompletedProcess(argv, 0, json.dumps([{"Id": "c" * 64, "Name": "/" + decision["container_name"], "Config": {"Image": runtime_image}, "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True}}]), "")
            return subprocess.CompletedProcess(argv, 1, "", "No such container")
        assert argv == ["docker", "rm", "-f", "c" * 64]
        existing[0] = False
        return subprocess.CompletedProcess(argv, 0, "c" * 64, "")

    monkeypatch.setattr(subprocess, "run", docker)
    result = engine.invoke("recover", {"job": job["job_id"], "attempt": attempt["attempt_id"], "grant": sign(key, decision)})
    assert result["retired"] is True and result["fresh_exact_operation_grant_required"] is True
    assert result["state"] == ("BLOCKED_PREREQUISITE" if source_changed else "BASELINE_AUTHORITY_REQUIRED")
    assert engine.store.attempts_for(job["job_id"])[0]["state"] == "RETIRED"
    assert engine.store.get(job["job_id"])["execution_receipts"] == []
    assert not existing[0] and len(calls) == 4
    with pytest.raises(ContractError, match="fenc|ownership"):
        engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "AUTHORITY_CLAIMED", {"late": True}, now=101)


def test_recovery_cannot_retire_one_attempt_while_another_attempt_owns_the_job(tmp_path, monkeypatch):
    engine, job, first, key, _ = control_fixture(tmp_path)
    second = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "other_attempt", "timeout_seconds": 20, "output_limit_bytes": 65536})
    engine.store.claim_attempt(job["job_id"], second["attempt_id"], "other_worker")
    decision = engine.invoke("control_request", {"job": job["job_id"], "attempt": first["attempt_id"], "actor": "fixture_owner", "purpose": "recover"})["decision"]
    before = (engine.store.root / "jobs.sqlite").read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Wrong-attempt recovery must not touch runtime or revoke the other worker")

    monkeypatch.setattr("subprocess.run", forbidden)
    with pytest.raises(ContractError, match="another|different"):
        engine.invoke("recover", {"job": job["job_id"], "attempt": first["attempt_id"], "grant": sign(key, decision)})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before

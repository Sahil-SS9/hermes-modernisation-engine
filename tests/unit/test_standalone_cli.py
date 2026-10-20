"""Standalone CLI shares strict input parsing and configured service behaviour."""

import base64
import json
import time
import uuid

from hermes_modernisation.__main__ import main
from hermes_modernisation.approvals import canonical
from test_review_requests import configured_fixture


def test_standalone_cli_accepts_exact_signed_review_through_the_same_service(tmp_path, capsys):
    engine, job, _, key, _, config = configured_fixture(tmp_path)
    prefix = ["--data-dir", str(engine.store.root), "--operator-config", str(config)]
    assert main(prefix + ["review_request", "--job", job["job_id"], "--purpose", "contract", "--actor", "fixture_owner"]) == 0
    draft = json.loads(capsys.readouterr().out)
    assert draft["permission_granted"] is False
    body = {"schema_version": 1, "decision": draft["decision"], "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
    grant = {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}
    assert main(prefix + ["review", "--job", job["job_id"], "--grant", json.dumps(grant)]) == 0
    assert json.loads(capsys.readouterr().out)["contract_review"]["authenticated"] is True


def test_standalone_cli_refuses_duplicate_nested_grant_fields_without_mutation(tmp_path, capsys):
    engine, job, _, _, _, config = configured_fixture(tmp_path)
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    result = main(["--data-dir", str(engine.store.root), "--operator-config", str(config), "review", "--job", job["job_id"], "--grant", '{"body":{"nonce":"one","nonce":"two"},"signature":"bad"}'])
    assert result == 2
    assert json.loads(capsys.readouterr().out)["error"] == "INVALID_ARGUMENTS"
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


def test_cli_does_not_claim_no_execution_after_an_ambiguous_start(tmp_path, capsys, monkeypatch):
    from hermes_modernisation.jsonio import ContractError
    from test_review_requests import signed_review

    engine, job, _, key, _, config = configured_fixture(tmp_path)
    engine.invoke("review", {"job": job["job_id"], "grant": signed_review(engine, job, key)})
    prepared = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "ambiguous_start", "timeout_seconds": 20, "output_limit_bytes": 65536})
    body = {"schema_version": 1, "operation": prepared["operation"], "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
    grant = {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}

    def injected_loss(executor, grant, operation, *unused):
        # Fault-injected journal mechanics; this test launches no Docker/program.
        executor.authority.claim(grant, operation)
        executor._checkpoint("AUTHORITY_CLAIMED", {"fixture": True})
        executor._checkpoint("START_REQUESTED", {"container_id": "c" * 64})
        raise ContractError("Injected connection loss after start request")

    def forbidden(*args, **kwargs):
        raise AssertionError("Fault fixture must not run a real process")

    monkeypatch.setattr("hermes_modernisation.controller.capture", injected_loss)
    monkeypatch.setattr("subprocess.run", forbidden)
    prefix = ["--data-dir", str(engine.store.root), "--operator-config", str(config)]
    assert main(prefix + ["run", "--job", job["job_id"], "--attempt", prepared["attempt_id"], "--grant", json.dumps(grant)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["execution_performed"] is None
    assert result["recovery_required"] is True
    assert result["attempt_id"] == prepared["attempt_id"]

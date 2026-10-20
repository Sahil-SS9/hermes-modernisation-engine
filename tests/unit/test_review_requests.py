"""Owner decision requests are data, separate from authority to run code."""

import base64
import hashlib
import time
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from hermes_modernisation.approvals import canonical

import pytest

from hermes_modernisation.jsonio import ContractError, dumps
from test_behaviour_contract import contract_fixture


def test_review_request_binds_the_registered_contract_without_granting_authority(tmp_path, monkeypatch):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})

    def forbidden(*args, **kwargs):
        raise AssertionError("Review request preparation must run nothing")

    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    database = engine.store.root / "jobs.sqlite"
    before = database.read_bytes()
    result = engine.invoke("review_request", {"job": job["job_id"], "purpose": "contract", "actor": "fixture_owner"})
    assert result["permission_granted"] is False
    assert result["execution_performed"] is False
    decision = result["decision"]
    assert decision == {
        "schema_version": 1, "kind": "ReviewDecision", "job_id": job["job_id"],
        "profile": "default", "actor": "fixture_owner", "purpose": "contract",
        "source_digest": job["assessment"]["source_digest"],
        "oracle_digest": hashlib.sha256(dumps(contract)).hexdigest(),
        "proposal_digest": None, "allowed_paths": contract["allowed_paths"],
    }
    assert "expected" not in str(result)
    assert database.read_bytes() == before
    assert engine.store.get(job["job_id"])["behaviour_contract"]["review_state"] == "unreviewed"


def test_migration_review_cannot_precede_a_captured_baseline_and_saved_proposal(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    with pytest.raises(ContractError, match="baseline|proposal"):
        engine.invoke("review_request", {"job": job["job_id"], "purpose": "migration", "actor": "fixture_owner"})


def test_missing_configuration_cannot_accept_owner_text_or_write_an_authority_store(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    database = engine.store.root / "jobs.sqlite"
    before = database.read_bytes()
    with pytest.raises(ContractError, match="EXECUTION_UNAVAILABLE|trusted operator"):
        engine.invoke("review", {"job": job["job_id"], "grant": {"approved": True, "actor": "fixture_owner"}})
    assert database.read_bytes() == before
    assert not (tmp_path / "authority").exists()


def configured_fixture(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    key = Ed25519PrivateKey.generate()
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    config = tmp_path / "operator.json"
    config.write_bytes(dumps({
        "schema_version": 1, "profile": "default", "workspace": str(workspace),
        "public_keys": {"fixture_owner": base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()},
        "images": [contract["runtimes"]["baseline"]["image"]],
    }))
    config.chmod(0o600)
    # Trusted composition dependency, never an argument accepted by invoke().
    engine.operator_config = config
    return engine, job, contract, key, workspace, config


def signed_review(engine, job, key):
    decision = engine.invoke("review_request", {"job": job["job_id"], "purpose": "contract", "actor": "fixture_owner"})["decision"]
    body = {"schema_version": 1, "decision": decision, "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
    return {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}


def test_authentic_review_is_durable_but_is_not_execution_permission(tmp_path, monkeypatch):
    engine, job, contract, key, _, _ = configured_fixture(tmp_path)
    grant = signed_review(engine, job, key)

    def forbidden(*args, **kwargs):
        raise AssertionError("Accepting a review must not execute anything")

    monkeypatch.setattr("subprocess.run", forbidden)
    result = engine.invoke("review", {"job": job["job_id"], "grant": grant})
    assert result["state"] == "BASELINE_AUTHORITY_REQUIRED"
    assert result["contract_review"]["purpose"] == "contract"
    assert result["contract_review"]["oracle_digest"] == hashlib.sha256(dumps(contract)).hexdigest()
    assert result["contract_review"]["authenticated"] is True
    assert result["execution_receipts"] == []
    restored = type(engine)(engine.store.root)
    assert restored.invoke("status", {"job": job["job_id"]}) == result
    with pytest.raises((ContractError, PermissionError), match="consumed|replay|review"):
        engine.invoke("review", {"job": job["job_id"], "grant": grant})


@pytest.mark.parametrize("mutation", ["signature", "actor", "profile", "source", "extra", "expired"])
def test_review_tampering_is_rejected_before_any_job_write(tmp_path, mutation):
    engine, job, _, key, workspace, _ = configured_fixture(tmp_path)
    grant = signed_review(engine, job, key)
    if mutation == "signature":
        grant["signature"] = base64.b64encode(b"x" * 64).decode()
    elif mutation == "expired":
        grant["body"]["expires_at"] = 1
    else:
        field = {"actor": "actor", "profile": "profile", "source": "source_digest", "extra": "approved"}[mutation]
        grant["body"]["decision"][field] = "other" if mutation != "source" else "a" * 64
    if mutation != "signature":
        grant["signature"] = base64.b64encode(key.sign(canonical(grant["body"]))).decode()
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    with pytest.raises((ContractError, PermissionError)):
        engine.invoke("review", {"job": job["job_id"], "grant": grant})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before
    assert not (workspace / "control" / "claims.sqlite").exists()


def test_unsafe_trusted_settings_refuse_before_accepting_a_valid_signature(tmp_path):
    engine, job, _, key, _, config = configured_fixture(tmp_path)
    grant = signed_review(engine, job, key)
    config.chmod(0o644)
    with pytest.raises(ContractError, match="private|Unsafe"):
        engine.invoke("review", {"job": job["job_id"], "grant": grant})

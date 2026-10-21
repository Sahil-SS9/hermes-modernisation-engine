"""Owner-reviewed BusinessRule state is authenticated data, never a page edit.

The sealed lexical rule stays candidate-only. A separate signed decision binds
the exact rule digest the owner reviewed; coverage stays unverified until
protected executions link cases/assertions.
"""

import base64
import hashlib
import sqlite3
import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from hermes_modernisation.approvals import canonical
from hermes_modernisation.jsonio import ContractError, dumps, loads
from test_business_rule_contract import rule_fixture

ADEQUACY = "owner-asserted-adequate"


def configured_rule_fixture(tmp_path):
    engine, job, page = rule_fixture(tmp_path)
    key = Ed25519PrivateKey.generate()
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    config = tmp_path / "operator.json"
    config.write_bytes(dumps({
        "schema_version": 1, "profile": "default", "workspace": str(workspace),
        "public_keys": {"fixture_owner": base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()},
        "images": ["example/app@sha256:" + "a" * 64],
    }))
    config.chmod(0o600)
    engine.operator_config = config
    return engine, job, page, key


def rule_of(engine, job, page=None):
    if page is None:
        page = engine.invoke("inventory", {"job": job["job_id"], "section": "rules", "page": 0})
    return page["items"][0]


def signed(engine, job, key, *overrides):
    decision = engine.invoke(
        "rule_review_request",
        {"job": job["job_id"], "rule_id": rule_of(engine, job)["id"], "actor": "fixture_owner"},
    )["decision"]
    for name, value in overrides:
        decision[name] = value
    body = {
        "schema_version": 1,
        "decision": decision,
        "nonce": "fixture_" + uuid.uuid4().hex,
        "expires_at": time.time() + 300,
        "max_uses": 1,
    }
    return {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}


def test_request_is_data_only_and_binds_the_exact_rule_digest(tmp_path, monkeypatch):
    engine, job, page, _ = configured_rule_fixture(tmp_path)
    rule = rule_of(engine, job)

    def forbidden(*args, **kwargs):
        raise AssertionError("Rule review preparation must run nothing")

    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    database = engine.store.root / "jobs.sqlite"
    before = database.read_bytes()
    result = engine.invoke(
        "rule_review_request",
        {"job": job["job_id"], "rule_id": rule["id"], "actor": "fixture_owner"},
    )
    assert result["permission_granted"] is False
    assert result["execution_performed"] is False
    assert result["decision"] == {
        "schema_version": 1,
        "kind": "RuleReviewDecision",
        "job_id": job["job_id"],
        "profile": "default",
        "actor": "fixture_owner",
        "purpose": "rule",
        "source_digest": job["assessment"]["source_digest"],
        "rule_id": rule["id"],
        "rule_digest": hashlib.sha256(dumps(rule)).hexdigest(),
        "adequacy": ADEQUACY,
    }
    assert database.read_bytes() == before
    assert engine.store.get(job["job_id"])["assessment"] == job["assessment"]


def test_unknown_rule_cannot_be_requested(tmp_path):
    engine, job, page, _ = configured_rule_fixture(tmp_path)
    with pytest.raises(ContractError, match="rule"):
        engine.invoke(
            "rule_review_request",
            {"job": job["job_id"], "rule_id": "rule-0000000000000000", "actor": "fixture_owner"},
        )


def test_authentic_review_is_stored_without_changing_job_state(tmp_path):
    engine, job, page, key = configured_rule_fixture(tmp_path)
    before = engine.invoke("status", {"job": job["job_id"]})
    grant = signed(engine, job, key)
    result = engine.invoke("rule_review", {"job": job["job_id"], "grant": grant})
    assert result["authenticated"] is True
    assert result["rule_id"] == rule_of(engine, job)["id"]
    assert result["adequacy"] == ADEQUACY
    assert engine.invoke("status", {"job": job["job_id"]}) == before
    listing = engine.invoke("rule_reviews", {"job": job["job_id"]})
    assert listing["coverage_status"] == "unverified"
    assert listing["permission_granted"] is False and listing["execution_performed"] is False
    assert len(listing["reviews"]) == 1
    stored = listing["reviews"][0]
    assert stored["id"] == result["id"]
    assert stored["rule_digest"] == result["rule_digest"]
    assert stored["current_rule_digest"] == result["rule_digest"]
    with pytest.raises((ContractError, PermissionError), match="consumed|replay|review|authority"):
        engine.invoke("rule_review", {"job": job["job_id"], "grant": grant})
    assert len(engine.invoke("rule_reviews", {"job": job["job_id"]})["reviews"]) == 1


@pytest.mark.parametrize(
    "mutation",
    ["signature", "actor", "profile", "source", "rule_id", "rule_digest", "adequacy", "extra", "expired"],
)
def test_tampered_rule_review_is_refused_before_any_write(tmp_path, mutation):
    engine, job, page, key = configured_rule_fixture(tmp_path)
    grant = signed(engine, job, key)
    if mutation == "signature":
        grant["signature"] = base64.b64encode(b"x" * 64).decode()
    elif mutation == "expired":
        grant["body"]["expires_at"] = 1
        grant["signature"] = base64.b64encode(key.sign(canonical(grant["body"]))).decode()
    else:
        field, value = {
            "actor": ("actor", "other_owner"),
            "profile": ("profile", "other"),
            "source": ("source_digest", "a" * 64),
            "rule_id": ("rule_id", "rule-0000000000000000"),
            "rule_digest": ("rule_digest", "b" * 64),
            "adequacy": ("adequacy", "proved"),
            "extra": ("statement", "owner says so"),
        }[mutation]
        grant["body"]["decision"][field] = value
        grant["signature"] = base64.b64encode(key.sign(canonical(grant["body"]))).decode()
    database = engine.store.root / "jobs.sqlite"
    before = database.read_bytes()
    with pytest.raises((ContractError, PermissionError), match="rule|review|authority|signature|decision|stale|owner|[Ee]xpired"):
        engine.invoke("rule_review", {"job": job["job_id"], "grant": grant})
    assert database.read_bytes() == before


def test_rule_review_listing_requires_trusted_configuration(tmp_path):
    engine, job, page, key = configured_rule_fixture(tmp_path)
    engine.invoke("rule_review", {"job": job["job_id"], "grant": signed(engine, job, key)})
    engine.operator_config = None
    with pytest.raises(ContractError, match="EXECUTION_UNAVAILABLE|trusted operator"):
        engine.invoke("rule_reviews", {"job": job["job_id"]})


def test_rehashed_stored_review_is_refused_on_read(tmp_path):
    engine, job, page, key = configured_rule_fixture(tmp_path)
    engine.invoke("rule_review", {"job": job["job_id"], "grant": signed(engine, job, key)})
    database = engine.store.root / "jobs.sqlite"
    with sqlite3.connect(database) as connection:
        raw = connection.execute(
            "SELECT id,body FROM reviews WHERE job_id=? AND purpose='rule'", (job["job_id"],)
        ).fetchone()
        body = loads(raw[1])
        body["reference"]["adequacy"] = "proved"
        changed = dumps(body)
        connection.execute(
            "UPDATE reviews SET body=?, body_sha256=? WHERE id=?",
            (changed, hashlib.sha256(changed).hexdigest(), raw[0]),
        )
    with pytest.raises(ContractError, match="review|rule|decision"):
        engine.invoke("rule_reviews", {"job": job["job_id"]})

"""Durable preparation/claim mechanics; fixture keys do not authorise real jobs."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from hermes_modernisation.jsonio import ContractError
from test_behaviour_contract import contract_fixture


def prepared_fixture(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    args = {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "baseline_prepare", "timeout_seconds": 20, "output_limit_bytes": 65536}
    return engine, job, args


def test_public_prepare_is_durable_idempotent_and_never_permission(tmp_path, monkeypatch):
    engine, job, args = prepared_fixture(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Preparing an unsigned request must not execute")

    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    first = engine.invoke("prepare", args)
    assert first["state"] == "PREPARED"
    assert first["permission_granted"] is False
    assert first["execution_performed"] is False
    assert first["operation"]["job_id"] == job["job_id"]
    assert first["operation"]["oracle_digest"] == engine.store.get(job["job_id"])["behaviour_contract"]["digest"]
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    assert engine.invoke("prepare", args) == first
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before
    attempts = engine.invoke("attempts", {"job": job["job_id"]})["attempts"]
    assert attempts == [first]
    assert "lease_token" not in str(attempts)
    # New stores start at v4; legacy upgrade/backup is tested from actual v3 below.


def test_same_preparation_key_cannot_rebind_changed_limits(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    first = engine.invoke("prepare", args)
    with pytest.raises(ContractError, match="Idempotency"):
        engine.invoke("prepare", {**args, "timeout_seconds": 21})
    assert engine.invoke("attempts", {"job": job["job_id"]})["attempts"] == [first]


def test_two_concurrent_preparations_have_one_stored_identity(tmp_path):
    engine, _, args = prepared_fixture(tmp_path)
    barrier = threading.Barrier(2)

    def call():
        barrier.wait(timeout=5)
        return engine.invoke("prepare", args)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: call(), range(2)))
    assert results[0] == results[1]
    assert len(engine.invoke("attempts", {"job": args["job"]})["attempts"]) == 1


def test_claim_fencing_and_expired_lease_require_recovery_not_replay(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    attempt = engine.invoke("prepare", args)
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker_one", now=100, lease_seconds=60)
    with pytest.raises(ContractError, match="active|claimed|recovery"):
        engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker_two", now=101, lease_seconds=60)
    with pytest.raises(ContractError, match="recovery"):
        engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker_two", now=200, lease_seconds=60)
    engine.store.stop_attempt(job["job_id"], attempt["attempt_id"], lease, "INTERRUPTED", "fixture process loss", now=102)
    with pytest.raises(ContractError, match="fenc|stale|ownership"):
        engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "COLLECTED", {"forged": "late result"}, now=103)
    assert engine.invoke("attempts", {"job": job["job_id"]})["attempts"][0]["state"] == "INTERRUPTED"


def test_candidate_preparation_cannot_take_a_caller_digest_or_skip_baseline(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    with pytest.raises(ContractError, match="candidate|baseline"):
        engine.invoke("prepare", {**args, "phase": "candidate"})
    with pytest.raises(ContractError, match="argument"):
        engine.invoke("prepare", {**args, "candidate_digest": "a" * 64})
    assert engine.invoke("attempts", {"job": job["job_id"]})["attempts"] == []


def test_real_v3_upgrade_keeps_jobs_blobs_and_reported_evidence(tmp_path):
    import hashlib
    import sqlite3
    from hermes_modernisation.jsonio import dumps
    from hermes_modernisation.store import Store

    root = tmp_path / "v3_private"
    root.mkdir(mode=0o700)
    db = root / "jobs.sqlite"
    legacy_job = {"schema_version": 1, "kind": "AssessmentJob", "job_id": "legacy", "revision": 0, "state": "ASSESSED"}
    raw = dumps({"legacy_report": "reported_only"})
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL, body BLOB NOT NULL)")
        connection.execute("CREATE TABLE details (hash TEXT PRIMARY KEY, body BLOB NOT NULL)")
        connection.execute("CREATE TABLE evaluations (job_id TEXT NOT NULL, phase TEXT NOT NULL, source_digest TEXT NOT NULL, expectation_digest TEXT NOT NULL, body BLOB NOT NULL, body_sha256 TEXT NOT NULL, UNIQUE(job_id,phase))")
        connection.execute("INSERT INTO jobs VALUES (?,?,?,?)", ("legacy", "legacy_request", "legacy_fingerprint", dumps(legacy_job)))
        connection.execute("INSERT INTO details VALUES (?,?)", ("opaque_legacy_blob", b"legacy bytes"))
        connection.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,?)", ("legacy", "baseline", "a" * 64, "b" * 64, raw, hashlib.sha256(raw).hexdigest()))
        connection.execute("PRAGMA user_version=3")
    db.chmod(0o600)
    before = db.read_bytes()
    store = Store(root)
    assert store.attempts_for("legacy") == []
    assert db.read_bytes() == before
    store.migrate()
    with sqlite3.connect(root / "jobs.pre-v4.sqlite") as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 3
        assert backup.execute("SELECT body FROM jobs").fetchone()[0] == dumps(legacy_job)
        assert backup.execute("SELECT body FROM evaluations").fetchone()[0] == raw
    with sqlite3.connect(db) as upgraded:
        assert upgraded.execute("PRAGMA user_version").fetchone()[0] == 4
        assert upgraded.execute("SELECT body FROM details").fetchone()[0] == b"legacy bytes"
        assert upgraded.execute("SELECT body FROM evaluations").fetchone()[0] == raw
        assert upgraded.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert upgraded.execute("PRAGMA foreign_key_check").fetchall() == []
    assert store.get("legacy") == legacy_job
    assert store.attempts_for("legacy") == []


def test_two_workers_cannot_claim_the_same_prepared_attempt(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    attempt = engine.invoke("prepare", args)
    barrier = threading.Barrier(2)

    def call(worker):
        barrier.wait(timeout=5)
        try:
            return engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], worker, now=100, lease_seconds=60)
        except ContractError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(call, ["worker_a", "worker_b"]))
    assert sum(type(result) is dict for result in results) == 1
    assert sum(type(result) is str and "active" in result for result in results) == 1


def test_contract_change_invalidates_a_prepared_attempt_before_claim(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    attempt = engine.invoke("prepare", args)
    contract = engine.store.contract_for(job["job_id"])
    contract["seed"] += 1
    engine.invoke("contract", {"job": job["job_id"], "revision": engine.store.get(job["job_id"])["revision"], "contract": contract})
    with pytest.raises(ContractError, match="stale"):
        engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    assert engine.invoke("attempts", {"job": job["job_id"]})["attempts"][0]["state"] == "PREPARED"


def test_an_interrupted_job_cannot_claim_a_different_prepared_attempt_without_recovery(tmp_path):
    engine, job, args = prepared_fixture(tmp_path)
    first = engine.invoke("prepare", args)
    second = engine.invoke("prepare", {**args, "request_id": "second_attempt"})
    lease = engine.store.claim_attempt(job["job_id"], first["attempt_id"], "worker", now=100, lease_seconds=60)
    engine.store.stop_attempt(job["job_id"], first["attempt_id"], lease, "INTERRUPTED", "uncertain runtime", now=101)
    with pytest.raises(ContractError, match="recovery"):
        engine.store.claim_attempt(job["job_id"], second["attempt_id"], "other_worker", now=102, lease_seconds=60)


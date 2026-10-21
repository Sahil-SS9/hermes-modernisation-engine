"""Exhaustive declared state/profile/concurrency matrix for claim ownership.

These cells are the authority contract, not happy-path examples: every job state
is exercised for both phases, every attempt state for ownership, the checkpoint
order in full, every stop outcome, profile isolation and same-lease races.
"""

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from hermes_modernisation import state
from hermes_modernisation.jsonio import ContractError, dumps, loads
from hermes_modernisation.models import STATES
from test_behaviour_contract import contract_fixture

BASELINE_ELIGIBLE = {"BASELINE_AUTHORITY_REQUIRED"}
CANDIDATE_ELIGIBLE = {"CANDIDATE_BUILT", "CANDIDATE_AUTHORITY_REQUIRED"}


def matrix_fixture(tmp_path, phase):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    if phase == "baseline":
        attempt = engine.invoke("prepare", {
            "job": job["job_id"], "phase": "baseline", "actor": "fixture_owner",
            "request_id": "baseline_prepare", "timeout_seconds": 20, "output_limit_bytes": 65536,
        })
    else:
        oracle = hashlib.sha256(dumps(contract)).hexdigest()

        def factory(aid):
            return {
                "schema_version": 1, "job_id": job["job_id"], "attempt_id": aid,
                "actor": "fixture_owner", "profile": "default",
                "source_digest": job["assessment"]["source_digest"],
                "candidate_digest": job["assessment"]["source_digest"],
                "oracle_digest": oracle, "environment_digest": "0" * 64,
                "image_digest": "a" * 64, "argv": ["python", "-m", "candidate"],
                "read_roots": ["/source"], "write_roots": ["/tmp", "/work"], "network": "none",
                "timeout_seconds": 20, "output_limit_bytes": 65536,
            }

        attempt = state.prepare(
            engine.store, job["job_id"], "candidate_prepare",
            {"phase": "candidate", "oracle_digest": oracle}, factory,
        )
    return engine, job, attempt


def set_job_state(engine, job_id, value):
    job = engine.store.get(job_id)
    job["state"] = value
    with engine.store.connection() as connection:
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(job), job_id))


def set_attempt_state(engine, job_id, attempt_id, value):
    with engine.store.connection() as connection:
        row = connection.execute("SELECT body FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        body = loads(row[0])
        body["state"] = value
        if value in {"RUNNING", "CLAIMED", "COLLECTED"}:
            body["_lease"] = {"worker": "w", "token_hash": "0" * 64, "until": 0}
        connection.execute(
            "UPDATE attempts SET state=?,body=? WHERE id=?", (value, dumps(body), attempt_id)
        )


@pytest.mark.parametrize("phase", ["baseline", "candidate"])
@pytest.mark.parametrize("job_state", sorted(STATES))
def test_claim_is_allowed_only_in_the_declared_job_states(tmp_path, phase, job_state):
    engine, job, attempt = matrix_fixture(tmp_path, phase)
    eligible = BASELINE_ELIGIBLE if phase == "baseline" else CANDIDATE_ELIGIBLE
    set_job_state(engine, job["job_id"], job_state)
    if job_state in eligible:
        lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
        assert type(lease["fence"]) is int and lease["fence"] >= 1
        stored = engine.invoke("attempts", {"job": job["job_id"]})["attempts"][0]
        assert stored["state"] == "RUNNING"
    else:
        with pytest.raises(ContractError, match="state|recovery|active"):
            engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)


ATTEMPT_STATES = ["PREPARED", "RUNNING", "CLAIMED", "COLLECTED", "COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED", "RETIRED"]


@pytest.mark.parametrize("attempt_state", ATTEMPT_STATES)
def test_claim_is_allowed_only_for_a_prepared_attempt(tmp_path, attempt_state):
    engine, job, attempt = matrix_fixture(tmp_path, "baseline")
    set_attempt_state(engine, job["job_id"], attempt["attempt_id"], attempt_state)
    if attempt_state == "PREPARED":
        engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    else:
        with pytest.raises(ContractError, match="recovery|active|terminal"):
            engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)


def test_checkpoint_order_and_idempotency_are_exhaustive(tmp_path):
    engine, job, attempt = matrix_fixture(tmp_path, "baseline")
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    steps = [
        ("AUTHORITY_CLAIMED", {"a": 1}),
        ("START_REQUESTED", {"b": 2}),
        ("COLLECTED", {"c": 3}),
        ("CLEANUP_VERIFIED", {"d": 4}),
    ]
    for index, (label, details) in enumerate(steps):
        if index + 1 < len(steps):
            with pytest.raises(ContractError, match="order"):
                engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, steps[index + 1][0], {}, now=101)
        engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, label, details, now=101 + index)
        assert engine.invoke("attempts", {"job": job["job_id"]})["attempts"][0]["checkpoints"][-1]["label"] == label
    recorded = engine.invoke("attempts", {"job": job["job_id"]})["attempts"][0]
    same = engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "CLEANUP_VERIFIED", {"d": 4}, now=150)
    assert same["checkpoints"] == recorded["checkpoints"]
    with pytest.raises(ContractError, match="changed"):
        engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "CLEANUP_VERIFIED", {"d": 5}, now=150)
    with pytest.raises(ContractError, match="Unsupported execution checkpoint"):
        engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "DONE", {}, now=150)


@pytest.mark.parametrize("outcome", ["FAILED", "CANCELLED", "INTERRUPTED"])
def test_stop_outcomes_are_exhaustive_and_terminal(tmp_path, outcome):
    engine, job, attempt = matrix_fixture(tmp_path, "baseline")
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    stopped = engine.store.stop_attempt(job["job_id"], attempt["attempt_id"], lease, outcome, "matrix reason", now=101)
    assert stopped["state"] == outcome
    assert engine.store.get(job["job_id"])["state"] == outcome
    with pytest.raises(ContractError, match="fenc|stale|ownership|recovery"):
        engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "AUTHORITY_CLAIMED", {}, now=102)


def test_stop_refuses_unowned_or_invalid_requests(tmp_path):
    engine, job, attempt = matrix_fixture(tmp_path, "baseline")
    with pytest.raises(ContractError, match="fenc|ownership"):
        engine.store.stop_attempt(job["job_id"], attempt["attempt_id"], {"fence": 0, "token": "x", "worker": "w"}, "FAILED", "reason", now=100)
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    with pytest.raises(ContractError, match="outcome|interruption"):
        engine.store.stop_attempt(job["job_id"], attempt["attempt_id"], lease, "DONE", "reason", now=101)
    with pytest.raises(ContractError, match="outcome|interruption"):
        engine.store.stop_attempt(job["job_id"], attempt["attempt_id"], lease, "FAILED", "", now=101)


def cross_profile_fixture(tmp_path):
    engine, job, attempt = matrix_fixture(tmp_path, "baseline")
    other = type(engine)(engine.store.root, profile="other")
    with pytest.raises(ContractError, match="scope|not found"):
        other.invoke("status", {"job": job["job_id"]})
    lease = {"fence": 1, "token": "x", "worker": "worker"}
    return engine, other, job, attempt, lease


def test_cross_profile_claim_is_refused(tmp_path):
    engine, other, job, attempt, _ = cross_profile_fixture(tmp_path)
    with pytest.raises(ContractError, match="scope|not found"):
        other.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    assert engine.invoke("status", {"job": job["job_id"]})["state"] == "BASELINE_AUTHORITY_REQUIRED"


def test_cross_profile_checkpoint_is_refused(tmp_path):
    _, other, job, attempt, lease = cross_profile_fixture(tmp_path)
    with pytest.raises(ContractError, match="scope|not found"):
        other.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "AUTHORITY_CLAIMED", {}, now=100)


def test_cross_profile_stop_is_refused(tmp_path):
    _, other, job, attempt, lease = cross_profile_fixture(tmp_path)
    with pytest.raises(ContractError, match="scope|not found"):
        other.store.stop_attempt(job["job_id"], attempt["attempt_id"], lease, "FAILED", "cross profile", now=100)


def test_cross_profile_prepare_is_refused_before_building_an_operation(tmp_path):
    engine, other, job, _, _ = cross_profile_fixture(tmp_path)
    with pytest.raises(ContractError, match="scope|not found"):
        state.prepare(
            other.store, job["job_id"], "cross_profile",
            {"phase": "baseline", "oracle_digest": engine.store.get(job["job_id"])["behaviour_contract"]["digest"]},
            lambda aid: (_ for _ in ()).throw(AssertionError("operation must not be built")),
        )


def test_two_profiles_can_hold_their_own_lease_concurrently(tmp_path):
    default_root = tmp_path / "default_root"
    default_root.mkdir()
    other_root = tmp_path / "other_root"
    other_root.mkdir()
    default, default_job, _ = matrix_fixture(default_root, "baseline")
    other, other_job, _ = matrix_fixture(other_root, "baseline")
    barrier = threading.Barrier(2)

    def claim(engine, job, attempt, worker):
        barrier.wait(timeout=5)
        return engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], worker, now=100, lease_seconds=60)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(claim, default, default_job, default.invoke("attempts", {"job": default_job["job_id"]})["attempts"][0], "w1")
        second = pool.submit(claim, other, other_job, other.invoke("attempts", {"job": other_job["job_id"]})["attempts"][0], "w1")
        assert first.result()["fence"] == second.result()["fence"] == 1


def test_same_lease_checkpoint_races_are_idempotent_or_refused(tmp_path):
    engine, job, attempt = matrix_fixture(tmp_path, "baseline")
    lease = engine.store.claim_attempt(job["job_id"], attempt["attempt_id"], "worker", now=100, lease_seconds=60)
    barrier = threading.Barrier(2)

    def checkpoint(details):
        barrier.wait(timeout=5)
        try:
            engine.store.checkpoint_attempt(job["job_id"], attempt["attempt_id"], lease, "AUTHORITY_CLAIMED", details, now=101)
            return "ok"
        except ContractError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(checkpoint, [{"a": 1}, {"a": 1}]))
    assert results == ["ok", "ok"]
    stored = engine.invoke("attempts", {"job": job["job_id"]})["attempts"][0]
    assert [entry["label"] for entry in stored["checkpoints"]] == ["AUTHORITY_CLAIMED"]

    race_root = tmp_path / "race"
    race_root.mkdir()
    engine2, job2, attempt2 = matrix_fixture(race_root, "baseline")
    lease2 = engine2.store.claim_attempt(job2["job_id"], attempt2["attempt_id"], "worker", now=100, lease_seconds=60)
    barrier2 = threading.Barrier(2)

    def conflicting(details):
        barrier2.wait(timeout=5)
        try:
            engine2.store.checkpoint_attempt(job2["job_id"], attempt2["attempt_id"], lease2, "AUTHORITY_CLAIMED", details, now=101)
            return "ok"
        except ContractError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(conflicting, [{"a": 1}, {"a": 2}]))
    assert results.count("ok") == 1
    assert sum("changed" in result for result in results) == 1

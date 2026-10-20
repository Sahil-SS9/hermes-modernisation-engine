"""Configured public execution refuses forged data before runtime or job writes."""

import pytest

from hermes_modernisation.jsonio import ContractError
from test_review_requests import configured_fixture, signed_review


def test_run_requires_review_and_an_exact_prepared_attempt_not_just_an_actor(tmp_path, monkeypatch):
    engine, job, _, _, _, _ = configured_fixture(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unreviewed/unsigned requests must not reach the runtime")

    monkeypatch.setattr("subprocess.run", forbidden)
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    with pytest.raises((ContractError, PermissionError), match="review|authority|signed"):
        engine.invoke("run", {"job": job["job_id"], "attempt": "forged", "grant": {"approved": True}})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


def test_authentic_review_cannot_be_reused_as_a_process_grant(tmp_path, monkeypatch):
    engine, job, _, key, _, _ = configured_fixture(tmp_path)
    grant = signed_review(engine, job, key)
    engine.invoke("review", {"job": job["job_id"], "grant": grant})
    prepared = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "real_request", "timeout_seconds": 20, "output_limit_bytes": 65536})

    def forbidden(*args, **kwargs):
        raise AssertionError("Review permission is not permission to run")

    monkeypatch.setattr("subprocess.run", forbidden)
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    with pytest.raises((ContractError, PermissionError), match="grant|operation|authority"):
        engine.invoke("run", {"job": job["job_id"], "attempt": prepared["attempt_id"], "grant": grant})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before
    assert engine.store.attempts_for(job["job_id"])[0]["state"] == "PREPARED"


def test_public_proposal_cannot_skip_the_observed_baseline(tmp_path):
    engine, job, _, _, _, _ = configured_fixture(tmp_path)
    with pytest.raises(ContractError, match="baseline"):
        engine.invoke("proposal", {"job": job["job_id"], "revision": 1, "proposal": {"approved": True}})


def test_build_uses_no_caller_supplied_destination_or_candidate_digest(tmp_path):
    engine, job, _, _, _, _ = configured_fixture(tmp_path)
    with pytest.raises(ContractError, match="argument"):
        engine.invoke("build", {"job": job["job_id"], "dest": str(tmp_path / "arbitrary"), "candidate_digest": "a" * 64})


def test_resume_never_blindly_replays_a_prepared_or_uncertain_attempt(tmp_path, monkeypatch):
    engine, job, _, _, _, _ = configured_fixture(tmp_path)
    prepared = engine.invoke("prepare", {"job": job["job_id"], "phase": "baseline", "actor": "fixture_owner", "request_id": "uncertain", "timeout_seconds": 20, "output_limit_bytes": 65536})
    engine.store.claim_attempt(job["job_id"], prepared["attempt_id"], "lost_worker", now=100, lease_seconds=1)

    def forbidden(*args, **kwargs):
        raise AssertionError("Resume must not start a process or reuse old permission")

    monkeypatch.setattr("subprocess.run", forbidden)
    with pytest.raises(ContractError, match="recovery|uncertain|replay"):
        engine.invoke("resume", {"job": job["job_id"], "attempt": prepared["attempt_id"]})

import pytest
from concurrent.futures import ThreadPoolExecutor
from hermes_modernisation.store import Store
from hermes_modernisation.jsonio import ContractError


def test_create_restart_idempotency_and_revision(tmp_path):
    root = tmp_path / "data"
    store = Store(root)
    first = store.create(
        "request-one", "/source", "upgrade", {"source_digest": "a" * 64}
    )
    assert first["state"] == "ASSESSED" and first["revision"] == 0
    assert Store(root).get(first["job_id"]) == first
    assert (
        store.create("request-one", "/source", "upgrade", {"source_digest": "a" * 64})
        == first
    )
    with pytest.raises(ContractError):
        store.create("request-one", "/source", "different", {"source_digest": "a" * 64})
    updated = store.save_plan(first["job_id"], 0, {"goal": "review required"})
    assert (
        updated["revision"] == 1 and updated["state"] == "BASELINE_AUTHORITY_REQUIRED"
    )
    with pytest.raises(ContractError):
        store.save_plan(first["job_id"], 0, {"goal": "stale"})
    assert store.get(first["job_id"]) == updated


def test_concurrent_create_same_request_is_one_job(tmp_path):
    store = Store(tmp_path / "private")

    def create(_):
        return store.create(
            "same-request", "/source", "goal", {"source_digest": "a" * 64}
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(create, range(4)))
    assert len({result["job_id"] for result in results}) == 1


def test_scopes_and_invalid_ids(tmp_path):
    one = Store(tmp_path / "profile-one")
    two = Store(tmp_path / "profile-two")
    job = one.create("one", "/source", "goal", {"source_digest": "a" * 64})
    with pytest.raises(ContractError):
        two.get(job["job_id"])
    for value in ("../escape", "a/b", "", "x" * 200):
        with pytest.raises(ContractError):
            one.get(value)


def test_symlink_store_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ContractError):
        Store(alias).create("request", "/source", "goal", {"source_digest": "a" * 64})

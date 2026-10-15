import pytest
from hermes_modernisation.store import Store
from hermes_modernisation.jsonio import ContractError


def test_queries_do_not_create_or_change_private_state(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(ContractError):
        Store(missing).get("absent")
    assert not missing.exists(), "A read operation created private state"
    store = Store(tmp_path / "private")
    job = store.create("one", "/repo", "goal", {"source_digest": "a" * 64})
    path = store.root / "jobs.sqlite"
    before = path.read_bytes()
    assert store.get(job["job_id"]) == job
    assert path.read_bytes() == before, "Status rewrote database bytes"
    assert not (store.root / "jobs.sqlite-journal").exists()

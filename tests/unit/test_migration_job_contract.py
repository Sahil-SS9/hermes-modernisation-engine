"""New public jobs have a versioned, strict identity; legacy records stay legacy."""

import pytest

from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.service import Engine
from test_behaviour_contract import contract_fixture


def test_public_assessment_creates_an_explicit_migration_job_with_disabled_egress(tmp_path):
    engine, job, _ = contract_fixture(tmp_path)
    assert job["kind"] == "MigrationJob"
    assert type(job["schema_version"]) is int and job["schema_version"] == 1
    assert job["profile"] == "default"
    assert job["track"] is None
    assert job["adapter_version"] is None
    assert job["supported_behaviours"] == []
    assert job["model_policy"] == {"enabled": False, "egress_allowed": False, "provider": None, "model": None}
    assert job["budget"]["model_calls_limit"] == 0
    assert job["budget"]["model_calls_used"] == 0
    assert job["budget"]["actual_cost"] is None
    assert engine.invoke("status", {"job": job["job_id"]}) == job


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 2), ("revision", True),
    ("state", "AUTOMATICALLY_APPROVED"), ("profile", "other_profile"),
    ("approved", True), ("job_id", "b" * 32),
])
def test_corrupt_job_header_cannot_bypass_public_status(tmp_path, field, value):
    engine, job, _ = contract_fixture(tmp_path)
    changed = {**job, field: value}
    with engine.store.connection() as connection:
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(changed), job["job_id"]))
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    with pytest.raises(ContractError):
        engine.invoke("status", {"job": job["job_id"]})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


def test_contract_registration_binds_migration_metadata_without_self_review(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    result = engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    assert result["kind"] == "MigrationJob"
    assert result["track"] == contract["track"]
    assert result["adapter_version"] == contract["adapter"]
    assert result["supported_behaviours"] == [contract["scope"]]
    assert result["input_split"]["seed"] == contract["seed"]
    assert result["input_split"]["fresh"] == 10
    assert result["model_policy"]["egress_allowed"] is False
    assert result["behaviour_contract"]["review_state"] == "unreviewed"


def test_profile_binding_is_not_a_caller_supplied_status_selector(tmp_path):
    engine, job, _ = contract_fixture(tmp_path)
    other = Engine(engine.store.root, profile="other_profile")
    with pytest.raises(ContractError, match="profile|scope"):
        other.invoke("status", {"job": job["job_id"]})


def test_migration_schema_descriptor_is_read_only_and_matches_the_versioned_export(tmp_path):
    import hashlib
    import json
    from pathlib import Path

    root = tmp_path / "absent_private"
    result = Engine(root).invoke("schema", {"name": "migration-job-v1"})
    assert result["kind"] == "SchemaDescriptor" and result["execution_performed"] is False
    schema = result["schema"]
    assert schema["properties"]["kind"]["const"] == "MigrationJob"
    assert schema["additionalProperties"] is False
    assert {"profile", "state", "budget", "model_policy", "assessment"} <= set(schema["required"])
    assert result["sha256"] == hashlib.sha256(dumps(schema)).hexdigest()
    assert json.loads((Path("/source") / "schemas/migration-job-v1.json").read_text()) == schema
    assert not root.exists()


@pytest.mark.parametrize("field,value", [
    ("track", "transform"), ("supported_behaviours", ["unreviewed_database_effects"]),
    ("input_split", {"seed": 41, "fresh": 0, "boundary": 12, "malformed": 0, "state": 0, "property": 0, "metamorphic": 0, "concurrency": 0}),
    ("input_split", {"seed": 42, "fresh": 10, "boundary": 1, "malformed": 1, "state": 0, "property": 0, "metamorphic": 0, "concurrency": 0}),
])
def test_job_metadata_cannot_contradict_the_protected_contract_reference(tmp_path, field, value):
    engine, job, contract = contract_fixture(tmp_path)
    registered = engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    changed = {**registered, field: value}
    with engine.store.connection() as connection:
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(changed), job["job_id"]))
    with pytest.raises(ContractError, match="contract|metadata|scope"):
        engine.invoke("status", {"job": job["job_id"]})

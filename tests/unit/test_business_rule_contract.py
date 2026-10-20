"""Public rule data has a strict candidate contract, not self-certified coverage."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.service import Engine


def rule_fixture(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("def calculate(value):\n    assert value >= 0\n    return value * 2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke("assess", {"repo": str(source), "goal": "Keep behaviour", "request_id": "rules"})
    page = engine.invoke("inventory", {"job": job["job_id"], "section": "rules", "page": 0})
    return engine, job, page


def test_public_inventory_emits_source_bound_unreviewed_business_rule_candidates(tmp_path, monkeypatch):
    engine, job, page = rule_fixture(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Rule reads cannot launch programs or models")

    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    rule = page["items"][0]
    assert rule.get("kind") == "BusinessRule"
    assert type(rule["schema_version"]) is int and rule["schema_version"] == 1
    assert job["assessment"]["rule_schema"] == "business-rule-v1"
    assert rule["source_digest"] == job["assessment"]["source_digest"]
    assert rule["origin"] == "assertion-location-candidate"
    assert rule["text"] and rule["review_state"] == "unreviewed"
    assert rule["coverage_status"] == "unverified"
    assert rule["owner_reviewed"] is False and rule["assertion_adequacy"] == "unknown"
    assert rule["case_ids"] == rule["assertion_ids"] == []
    assert rule["unknowns"]
    assert rule["source_refs"] == [{"path": "app.py", "line_start": 2, "line_end": 2, "sha256": rule["source_sha256"]}]
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    assert engine.invoke("inventory", {"job": job["job_id"], "section": "rules", "page": 0}) == page
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 2), ("kind", "AssuredRule"),
    ("source_digest", "f" * 64), ("line", True), ("source_sha256", "f" * 64),
    ("coverage_status", "executed"), ("owner_reviewed", True),
    ("review_state", "reviewed"), ("assertion_adequacy", "proved"),
    ("case_ids", ["passing_test"]), ("assertion_ids", ["named_assertion"]),
    ("unknowns", []), ("text", False), ("unexpected", "accepted"),
    ("source_refs", [{"path": "../app.py", "line_start": 2, "line_end": 2, "sha256": "a" * 64}]),
])
def test_rehashed_rule_corruption_is_refused_on_the_public_read_path(tmp_path, field, value):
    engine, job, page = rule_fixture(tmp_path)
    changed = deepcopy(page["items"])
    changed[0][field] = value
    raw = dumps({"items": changed})
    sha = hashlib.sha256(raw).hexdigest()
    job["assessment"]["detail_pages"]["rules"][0] = sha
    with engine.store.connection() as connection:
        connection.execute("INSERT OR IGNORE INTO details VALUES (?,?)", (sha, raw))
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(job), job["job_id"]))
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    with pytest.raises(ContractError, match="rule|Rule|citation|digest|source|SHA|fields|count|integer|path"):
        engine.invoke("inventory", {"job": job["job_id"], "section": "rules", "page": 0})
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before


def test_rule_contract_cannot_be_downgraded_by_removing_its_version(tmp_path):
    engine, job, page = rule_fixture(tmp_path)
    changed = deepcopy(page["items"])
    changed[0].pop("schema_version", None)
    raw = dumps({"items": changed})
    sha = hashlib.sha256(raw).hexdigest()
    job["assessment"]["detail_pages"]["rules"][0] = sha
    with engine.store.connection() as connection:
        connection.execute("INSERT OR IGNORE INTO details VALUES (?,?)", (sha, raw))
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(job), job["job_id"]))
    with pytest.raises(ContractError):
        engine.invoke("inventory", {"job": job["job_id"], "section": "rules", "page": 0})


def test_business_rule_schema_descriptor_is_native_data_only_and_matches_the_export(tmp_path):
    root = tmp_path / "absent_private"
    result = Engine(root).invoke("schema", {"name": "business-rule-v1"})
    assert result["kind"] == "SchemaDescriptor" and result["permission_granted"] is False
    schema = result["schema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["kind"]["const"] == "BusinessRule"
    assert {"source_refs", "review_state", "case_ids", "assertion_ids", "coverage_status", "unknowns"} <= set(schema["required"])
    assert result["sha256"] == hashlib.sha256(dumps(schema)).hexdigest()
    assert json.loads(Path("/source/schemas/business-rule-v1.json").read_text()) == schema
    assert not root.exists()


def test_legacy_rule_pages_remain_readable_without_migration_or_new_proof_claims(tmp_path):
    engine = Engine(tmp_path / "legacy_private")
    legacy = {"id": "legacy_rule", "kind": "assertion-location-candidate", "coverage_status": "unverified"}
    job = engine.store.create("legacy_rules", "/legacy", "legacy", {"source_digest": "a" * 64, "rules": [legacy]})
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    page = engine.invoke("inventory", {"job": job["job_id"], "section": "rules", "page": 0})
    assert page["items"] == [legacy]
    assert "rule_schema" not in engine.invoke("status", {"job": job["job_id"]})["assessment"]
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before

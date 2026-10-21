"""Public contract registration is data-only; it cannot bless its own checks."""

import hashlib
from copy import deepcopy

import pytest

from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.service import Engine

IMAGE = "modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6"


def contract_fixture(tmp_path):
    source = tmp_path / "legacy"
    source.mkdir()
    raw = b"def calculate(value):\n    return value * 2\n"
    (source / "app.py").write_bytes(raw)
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(source), "goal": "Keep the declared response behaviour", "request_id": "owned-contract-fixture"}
    )
    cases = [
        {"id": f"fresh_{i}", "kind": "fresh", "input": {"value": i}, "expected": {"value": i * 2}, "rule_ids": ["double"]}
        for i in range(10)
    ] + [
        {"id": "negative", "kind": "boundary", "input": {"value": -1}, "expected": {"value": -2}, "rule_ids": ["double"]},
        {"id": "malformed", "kind": "malformed", "input": {"value": "bad"}, "expected": {"error": "invalid"}, "rule_ids": ["double"]},
    ]
    contract = {
        "schema_version": 1,
        "kind": "BehaviourContract",
        "scope": "declared_pure_json_response",
        "track": "uplift",
        "source_digest": job["assessment"]["source_digest"],
        "adapter": "json-batch-v1",
        "runtimes": {phase: {"image": IMAGE, "argv": ["python", "-B", "/source/app.py"]} for phase in ("baseline", "candidate")},
        "allowed_paths": ["app.py"],
        "seed": 41,
        "rules": [{
            "id": "double", "text": "Double valid integers; invalid input has an explicit error response",
            "source_refs": [{"path": "app.py", "line_start": 1, "line_end": 2, "sha256": hashlib.sha256(raw).hexdigest()}],
            "case_ids": [case["id"] for case in cases],
        }],
        "cases": cases,
        "normalizations": [],
        "planned_differences": [],
    }
    return engine, job, contract


def test_public_contract_registration_persists_without_execution_or_self_approval(tmp_path, monkeypatch):
    engine, job, contract = contract_fixture(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Registering data must not launch code or a provider")

    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    registered = engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    assert registered["revision"] == 1
    assert registered["state"] == "BASELINE_AUTHORITY_REQUIRED"
    assert registered["behaviour_contract"]["review_state"] == "unreviewed"
    assert registered["behaviour_contract"]["case_count"] == 12
    assert registered["behaviour_contract"]["fresh_count"] == 10
    assert registered["execution_available"] is False
    assert "cases" not in registered["behaviour_contract"]
    restored = Engine(tmp_path / "private").invoke("status", {"job": job["job_id"]})
    assert restored == registered
    assert not any(source.name in ("oracle.json", "contract.json") for source in (tmp_path / "legacy").iterdir())


def test_typed_narrow_normalisation_is_accepted_into_the_sealed_contract(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    contract["normalizations"] = [
        {"case_id": "malformed", "operations": [{"op": "trim", "path": "error"}]}
    ]
    registered = engine.invoke(
        "contract", {"job": job["job_id"], "revision": 0, "contract": contract}
    )
    assert registered["behaviour_contract"]["review_state"] == "unreviewed"


@pytest.mark.parametrize(
    "entry",
    [
        {"case_id": "absent", "operations": [{"op": "trim", "path": "error"}]},
        {"case_id": "malformed", "operations": [{"op": "drop", "path": "*"}]},
        {
            "case_id": "malformed",
            "operations": [{"op": "trim", "path": "error"}, {"op": "lowercase", "path": "error"}],
        },
    ],
)
def test_broad_or_unknown_normalisations_are_refused(tmp_path, entry):
    engine, job, contract = contract_fixture(tmp_path)
    contract["normalizations"] = [entry]
    with pytest.raises(ContractError):
        engine.invoke(
            "contract", {"job": job["job_id"], "revision": 0, "contract": contract}
        )


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 2), ("review_state", "reviewed"),
    ("source_digest", "a" * 63), ("adapter", "self-reported-junit"),
    ("track", "anything"), ("seed", True), ("seed", -1),
    ("allowed_paths", ["../app.py"]), ("allowed_paths", ["tests/oracle.py"]),
    ("allowed_paths", [".github/workflows/ci.yaml"]),
    ("allowed_paths", ["requirements.txt"]),
    ("normalizations", [{"path": "*", "drop": True}]),
    ("planned_differences", [{"approved": True}]),
])
def test_invalid_contracts_cannot_mutate_job_or_storage(tmp_path, field, value):
    engine, job, contract = contract_fixture(tmp_path)
    contract[field] = value
    path = engine.store.root / "jobs.sqlite"
    before = path.read_bytes()
    with pytest.raises(ContractError):
        engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    assert path.read_bytes() == before
    assert engine.store.get(job["job_id"]) == job


@pytest.mark.parametrize("change", ["case_duplicate", "rule_missing", "case_missing", "fresh_repeated", "unknown_case_field", "bad_citation", "bool_citation", "unknown_runtime", "mutable_image", "empty_argv"])
def test_nested_contract_identity_collection_and_citations_are_checked(tmp_path, change):
    engine, job, contract = contract_fixture(tmp_path)
    if change == "case_duplicate":
        contract["cases"][1]["id"] = contract["cases"][0]["id"]
    elif change == "rule_missing":
        contract["cases"][0]["rule_ids"] = ["invented"]
    elif change == "case_missing":
        contract["rules"][0]["case_ids"].append("invented")
    elif change == "fresh_repeated":
        for case in contract["cases"][:10]:
            case["input"] = {"value": 0}
    elif change == "unknown_case_field":
        contract["cases"][0]["observed"] = True
    elif change == "bad_citation":
        contract["rules"][0]["source_refs"][0]["sha256"] = "a" * 64
    elif change == "bool_citation":
        contract["rules"][0]["source_refs"][0]["line_start"] = True
    elif change == "unknown_runtime":
        contract["runtimes"]["candidate"]["privileged"] = True
    elif change == "mutable_image":
        contract["runtimes"]["candidate"]["image"] = "python:latest"
    else:
        contract["runtimes"]["candidate"]["argv"] = []
    with pytest.raises(ContractError):
        engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    assert engine.store.get(job["job_id"]) == job


def test_contract_idempotent_retry_and_changed_revision_are_distinct(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    args = {"job": job["job_id"], "revision": 0, "contract": contract}
    first = engine.invoke("contract", args)
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    assert engine.invoke("contract", args) == first
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before
    changed = deepcopy(contract)
    changed["seed"] += 1
    with pytest.raises(ContractError, match="revision"):
        engine.invoke("contract", {**args, "contract": changed})
    assert engine.store.contract_for(job["job_id"]) == contract


def test_changed_source_cannot_reuse_contract_and_readback_detects_tamper(tmp_path):
    engine, job, contract = contract_fixture(tmp_path)
    engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    (tmp_path / "legacy" / "app.py").write_text("raise RuntimeError('changed')\n")
    with pytest.raises(ContractError, match="stale"):
        engine.invoke("contract", {"job": job["job_id"], "revision": 1, "contract": contract})
    with engine.store.connection() as connection:
        connection.execute("UPDATE details SET body=? WHERE hash=?", (dumps({"fake": "oracle"}), engine.store.get(job["job_id"])["behaviour_contract"]["digest"]))
    with pytest.raises(ContractError, match="corrupt"):
        engine.store.contract_for(job["job_id"])


def test_rehashed_unknown_fields_cannot_bypass_protected_contract_readback(tmp_path):
    from hermes_modernisation.contracts import contract_summary

    engine, job, contract = contract_fixture(tmp_path)
    saved = engine.invoke("contract", {"job": job["job_id"], "revision": 0, "contract": contract})
    altered = {**contract, "review_state": "reviewed"}
    summary = contract_summary(altered)
    saved["behaviour_contract"] = summary
    with engine.store.connection() as connection:
        connection.execute("INSERT INTO details VALUES (?,?)", (summary["digest"], dumps(altered)))
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(saved), job["job_id"]))
    with pytest.raises(ContractError, match="fields"):
        engine.store.contract_for(job["job_id"])

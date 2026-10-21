"""Evidence output contracts: receipts, comparisons and reports are data-only.

A receipt, comparison or rendered report that labels itself verified is still
candidate-authored bytes. These tests exercise the public read/collect paths
and refuse self-certification rather than trusting in-band claims.
"""

import hashlib
from pathlib import Path

import pytest

from hermes_modernisation.baseline import capture, make_inputs, wire_id
from hermes_modernisation.jsonio import ContractError, dumps, loads
from hermes_modernisation.service import Engine
from test_behaviour_contract import contract_fixture

ROOT = Path(__file__).resolve().parents[2]


def self_certified(job):
    return {
        "schema_version": 1,
        "job_id": job["job_id"],
        "scope": job["goal"],
        "source_digest": job["assessment"]["source_digest"],
        "verdict": "PROVEN",
        "execution_performed": True,
        "missing_evidence": [],
        "compared_cases": 0,
        "approved_differences": [],
    }


@pytest.mark.parametrize(
    "name",
    ["execution-receipt-v1", "evidence-comparison-v1", "proof-report-v1"],
)
def test_evidence_schema_descriptors_match_the_exported_contract(tmp_path, name):
    engine = Engine(tmp_path / "private")
    result = engine.invoke("schema", {"name": name})
    exported = loads((ROOT / "schemas" / f"{name}.json").read_bytes())
    assert result["schema"] == exported
    assert result["sha256"] == hashlib.sha256(dumps(exported)).hexdigest()
    assert result["permission_granted"] is False
    assert result["execution_performed"] is False


def test_public_compare_refuses_self_certified_observed_comparison(tmp_path, monkeypatch):
    engine, job, _ = contract_fixture(tmp_path)
    monkeypatch.setattr(
        "hermes_modernisation.observations.comparison",
        lambda store, job, policy: self_certified(job),
    )
    import types

    monkeypatch.setattr(
        "hermes_modernisation.operator.OperatorPolicy",
        lambda *args, **kwargs: types.SimpleNamespace(profile="default"),
    )
    real_get = engine.store.get

    def with_baseline(job_id):
        value = real_get(job_id)
        return {**value, "baseline_ref": {"attempt_id": "x"}} if job_id == job["job_id"] else value

    monkeypatch.setattr(engine.store, "get", with_baseline)
    with pytest.raises(ContractError, match="comparison|verdict|evidence"):
        engine.invoke("compare", {"job": job["job_id"]})


def test_public_compare_refuses_self_certified_reported_comparison(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "example.py").write_text("def double(x):\n    return x*2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(repo), "goal": "upgrade", "request_id": "one"}
    )
    monkeypatch.setattr(
        "hermes_modernisation.evidence.comparison",
        lambda job, recorded: self_certified(job),
    )
    with pytest.raises(ContractError, match="comparison|verdict|evidence"):
        engine.invoke("compare", {"job": job["job_id"]})
    with pytest.raises(ContractError, match="comparison|verdict|evidence"):
        engine.invoke("report", {"job": job["job_id"]})


def test_report_emits_a_bounded_not_proven_proof_report(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "example.py").write_text("def double(x):\n    return x*2\n")
    engine = Engine(tmp_path / "private")
    job = engine.invoke(
        "assess", {"repo": str(repo), "goal": "upgrade", "request_id": "one"}
    )
    comparison = engine.invoke("compare", {"job": job["job_id"]})
    report = engine.invoke("report", {"job": job["job_id"]})
    proof = report["proof_report"]
    assert proof["schema_version"] == 1 and proof["kind"] == "ProofReport"
    assert proof["verdict"] == "NOT_PROVEN"
    assert proof["claims"] == []
    assert proof["rule_coverage"] == "unverified"
    assert proof["execution_performed"] is False
    assert proof["comparison_sha256"] == hashlib.sha256(dumps(comparison)).hexdigest()
    assert loads(report["json"].encode()) == proof
    assert "NOT_PROVEN" in report["text"] and "NOT_PROVEN" in report["html"]


def _fake_capture(tmp_path, mutation=None):
    engine, job, contract = contract_fixture(tmp_path)
    aid = "attempt_one"
    operation = {
        "attempt_id": aid,
        "job_id": job["job_id"],
        "profile": "default",
        "source_digest": job["assessment"]["source_digest"],
        "oracle_digest": hashlib.sha256(dumps(contract)).hexdigest(),
        "environment_digest": "e" * 64,
        "output_limit_bytes": 65536,
    }
    payload = make_inputs(contract, aid)
    output = dumps(
        {
            "schema_version": 1,
            "results": [
                {"id": wire_id(aid, case["id"]), "output": case["expected"]}
                for case in contract["cases"]
            ],
        }
    )
    receipt = {
        "schema_version": 1,
        "kind": "ExecutionReceipt",
        "grade": "observed-process-only",
        "actor": "fixture_owner",
        "profile": "default",
        "job_id": operation["job_id"],
        "attempt_id": aid,
        "phase": "baseline",
        "source_digest": operation["source_digest"],
        "oracle_digest": operation["oracle_digest"],
        "environment_digest": operation["environment_digest"],
        "image": contract["runtimes"]["baseline"]["image"],
        "authority_nonce": "nonce",
        "process_exit_code": 0,
        "timed_out": False,
        "truncated": False,
        "output_bytes": len(output),
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "input_bytes": len(payload),
        "input_complete": True,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "duration_seconds": 0.25,
        "container_removed": True,
        "source_unchanged": True,
        "verdict": "NOT_PROVEN",
        "missing_evidence": ["rule adequacy and mutation controls"],
    }
    if mutation == "extra":
        receipt["self_certified"] = True
    elif mutation == "grade":
        receipt["grade"] = "independently-verified"
    elif mutation == "kind":
        receipt["kind"] = "VerifiedReceipt"
    elif mutation == "missing_evidence":
        receipt["missing_evidence"] = []
    folder = tmp_path / "exec" / aid
    folder.mkdir(parents=True, mode=0o700)
    for name, raw in (
        ("receipt.json", dumps(receipt)),
        ("output.bin", output),
    ):
        path = folder / name
        path.write_bytes(raw)
        path.chmod(0o600)

    class FakeExecutor:
        input_data = payload
        phase = "baseline"
        image = contract["runtimes"]["baseline"]["image"]
        root = tmp_path / "exec"

        def run(self, grant, operation, source, oracle):
            return receipt

    return engine, job, contract, FakeExecutor(), operation


def test_conforming_receipt_is_accepted_with_its_version_marker(tmp_path):
    _, _, contract, executor, operation = _fake_capture(tmp_path)
    result = capture(executor, None, operation, None, None, contract)
    assert result["execution_performed"] is True
    assert result["receipt"]["kind"] == "ExecutionReceipt"
    assert result["evaluation"]["failed"] == 0


@pytest.mark.parametrize("mutation", ["extra", "grade", "kind", "missing_evidence"])
def test_capture_refuses_receipts_outside_the_versioned_contract(tmp_path, mutation):
    _, _, contract, executor, operation = _fake_capture(tmp_path, mutation)
    with pytest.raises(ContractError, match="receipt|evidence"):
        capture(executor, None, operation, None, None, contract)

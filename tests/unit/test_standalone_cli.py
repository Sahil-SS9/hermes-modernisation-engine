"""Standalone CLI shares strict input parsing and configured service behaviour."""

import base64
import json
import time
import uuid

from hermes_modernisation.__main__ import main
from hermes_modernisation.approvals import canonical
from test_review_requests import configured_fixture


def test_standalone_cli_accepts_exact_signed_review_through_the_same_service(tmp_path, capsys):
    engine, job, _, key, _, config = configured_fixture(tmp_path)
    prefix = ["--data-dir", str(engine.store.root), "--operator-config", str(config)]
    assert main(prefix + ["review_request", "--job", job["job_id"], "--purpose", "contract", "--actor", "fixture_owner"]) == 0
    draft = json.loads(capsys.readouterr().out)
    assert draft["permission_granted"] is False
    body = {"schema_version": 1, "decision": draft["decision"], "nonce": "fixture_" + uuid.uuid4().hex, "expires_at": time.time() + 300, "max_uses": 1}
    grant = {"body": body, "signature": base64.b64encode(key.sign(canonical(body))).decode()}
    assert main(prefix + ["review", "--job", job["job_id"], "--grant", json.dumps(grant)]) == 0
    assert json.loads(capsys.readouterr().out)["contract_review"]["authenticated"] is True


def test_standalone_cli_refuses_duplicate_nested_grant_fields_without_mutation(tmp_path, capsys):
    engine, job, _, _, _, config = configured_fixture(tmp_path)
    before = (engine.store.root / "jobs.sqlite").read_bytes()
    result = main(["--data-dir", str(engine.store.root), "--operator-config", str(config), "review", "--job", job["job_id"], "--grant", '{"body":{"nonce":"one","nonce":"two"},"signature":"bad"}'])
    assert result == 2
    assert json.loads(capsys.readouterr().out)["error"] == "INVALID_ARGUMENTS"
    assert (engine.store.root / "jobs.sqlite").read_bytes() == before

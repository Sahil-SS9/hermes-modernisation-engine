"""Pure execution declarations shared by request preparation and the executor.

Constructing these values does not check runtime availability or grant authority.
No Docker, model facade, credentials or optional crypto are imported here.
"""

import hashlib
from pathlib import Path

from .identity import snapshot
from .jsonio import ContractError, dumps
from .operations import AuthorityDenied, validate_operation


def environment_spec(operation, image, phase, input_sha256=None):
    value = {
        "schema_version": 1, "image": image, "argv": operation["argv"],
        "oracle_digest": operation["oracle_digest"], "network": "none",
        "readonly_source": True, "collector": "bounded-process-v1",
        "source_identity": "files-and-dirs-v2", "phase": phase,
        "engine_core_digest": snapshot(Path(__file__).parent)["digest"],
    }
    if input_sha256 is not None:
        value.update(collector="bounded-json-response-v1", input_sha256=input_sha256)
    return value


def prepare_request(store, job, arguments, *, profile="default"):
    from . import state

    phase = arguments["phase"]
    if type(phase) is not str or phase not in ("baseline", "candidate"):
        raise ContractError("Unsupported baseline/candidate phase")
    contract = store.contract_for(job["job_id"])
    if phase == "baseline":
        source_digest = job["assessment"]["source_digest"]
    else:
        # This is an engine-owned reference, never the caller's digest/path.
        candidate = job.get("candidate_ref")
        if not candidate or job["state"] not in {"CANDIDATE_BUILT", "CANDIDATE_AUTHORITY_REQUIRED"}:
            raise ContractError("Protected baseline and approved engine-owned candidate required")
        source_digest = candidate["candidate_digest"]
    runtime = contract["runtimes"][phase]
    blueprint = {
        "phase": phase, "profile": profile, "actor": arguments["actor"],
        "source_digest": source_digest, "oracle_digest": job["behaviour_contract"]["digest"],
        "runtime": runtime, "timeout_seconds": arguments["timeout_seconds"],
        "output_limit_bytes": arguments["output_limit_bytes"],
        "engine_core_digest": snapshot(Path(__file__).parent)["digest"],
        "candidate_ref": job.get("candidate_ref") if phase == "candidate" else None,
    }

    def operation_factory(aid):
        operation = {
            "schema_version": 1, "job_id": job["job_id"], "attempt_id": aid,
            "actor": arguments["actor"], "profile": profile,
            "source_digest": source_digest, "candidate_digest": source_digest,
            "oracle_digest": blueprint["oracle_digest"], "environment_digest": "0" * 64,
            "image_digest": runtime["image"].split("@sha256:")[-1],
            "argv": runtime["argv"], "read_roots": ["/source"],
            "write_roots": ["/tmp", "/work"], "network": "none",
            "timeout_seconds": arguments["timeout_seconds"],
            "output_limit_bytes": arguments["output_limit_bytes"],
        }
        from .baseline import make_inputs
        payload = make_inputs(contract, aid)
        operation["environment_digest"] = hashlib.sha256(dumps(environment_spec(operation, runtime["image"], phase, hashlib.sha256(payload).hexdigest()))).hexdigest()
        try:
            validate_operation(operation)
        except AuthorityDenied as error:
            raise ContractError(str(error)) from error
        return operation

    # Validate the complete draft before even opening a write/migration transaction.
    operation_factory("validation_only")
    return state.prepare(store, job["job_id"], arguments["request_id"], blueprint, operation_factory)

"""Configured foreground execution controller. No signing, import promotion or replay.

The public service supplies only a stored attempt ID and an exact signed grant.
All paths, runtimes, protected inputs, collectors and state writes are resolved
from private state and trusted operator policy, outside the tested app.
"""

import hashlib
from pathlib import Path

from . import observations, reviews
from .baseline import capture, make_inputs
from .candidates import candidate_for
from .executor import Executor
from .identity import snapshot
from .jsonio import ContractError, dumps
from .state import _attempt


def prepared_attempt(store, job, attempt_id):
    with store.read_connection() as connection:
        return _attempt(connection, job["job_id"], attempt_id)


def run(store, job, attempt_id, grant, policy):
    reviews.accepted(store, job, "contract", policy)
    attempt = prepared_attempt(store, job, attempt_id)
    if attempt["state"] != "PREPARED":
        raise ContractError("Attempt is already claimed or terminal; recovery required, no automatic replay")
    phase = attempt["phase"]
    contract = store.contract_for(job["job_id"])
    if phase == "baseline":
        if job["state"] != "BASELINE_AUTHORITY_REQUIRED" or job.get("baseline_ref"):
            raise ContractError("Current baseline execution state/authority is not eligible")
        source = Path(job["repo"])
    else:
        if job["state"] not in {"CANDIDATE_BUILT", "CANDIDATE_AUTHORITY_REQUIRED"} or not job.get("baseline_ref"):
            raise ContractError("Protected passing baseline and engine-owned candidate required")
        reviews.accepted(store, job, "migration", policy)
        old = observations.read_one(store, job, job["baseline_ref"], policy)
        if old["failed"] or old["passed"] != old["expected"]:
            raise ContractError("Baseline failed the protected declared contract")
        source = Path(candidate_for(store, job, policy)["path"])
    operation = attempt["operation"]
    runtime = contract["runtimes"][phase]
    if runtime["image"] not in policy.images or operation["profile"] != policy.profile or operation["argv"] != runtime["argv"]:
        raise ContractError("Runtime image/command/profile differs from trusted policy")
    if operation["source_digest"] != snapshot(source)["digest"] or operation["oracle_digest"] != job["behaviour_contract"]["digest"]:
        raise ContractError("Prepared source/oracle identity is stale")
    payload = make_inputs(contract, attempt_id)
    authority = policy.authority()
    # Exact signature validation before ownership, workspace writes or Docker calls.
    authority.verify(grant, operation)
    executor = Executor(authority, policy.workspace / "executions", runtime["image"], profile=policy.profile, phase=phase, input_data=payload)
    if hashlib.sha256(dumps(executor.environment(operation))).hexdigest() != operation["environment_digest"]:
        raise ContractError("Prepared environment or engine core changed; create a fresh request")
    oracle_root = policy.workspace / "oracles"
    oracle_root.mkdir(mode=0o700, exist_ok=True)
    from .operator import private_directory
    private_directory(oracle_root)
    oracle = oracle_root / (operation["oracle_digest"] + ".json")
    if oracle.exists() or oracle.is_symlink():
        from .baseline import read_artifact
        if read_artifact(oracle, 1048576) != dumps(contract):
            raise ContractError("Protected oracle artifact changed")
    else:
        Executor._write(oracle, contract)
    executor.prepare(operation, source, oracle)
    lease = store.claim_attempt(job["job_id"], attempt_id, "foreground_controller", lease_seconds=operation["timeout_seconds"] + 120)

    def checkpoint(label, details):
        store.checkpoint_attempt(job["job_id"], attempt_id, lease, label, details)

    executor._checkpoint_callback = checkpoint
    try:
        captured = capture(executor, grant, operation, source, oracle, contract)
        return observations.complete(store, job["job_id"], attempt_id, lease, captured, grant)
    except BaseException:
        # Partial files and claimed authority stay retained. Never retry the side effect.
        try:
            store.stop_attempt(job["job_id"], attempt_id, lease, "INTERRUPTED", "Collection/acceptance interrupted; inspect retained runtime state and obtain explicit recovery, no replay")
        except ContractError:
            # A revoked/expired lease is intentionally not allowed to overwrite newer state.
            pass
        raise


def resume(store, job, attempt_id, policy):
    attempt = prepared_attempt(store, job, attempt_id)
    if attempt["state"] != "COMPLETED":
        raise ContractError("Prior execution is pending or uncertain; explicit recovery required, no replay")
    reference = job.get("baseline_ref") if attempt["phase"] == "baseline" else job.get("candidate_observation_ref")
    if not reference or reference["attempt_id"] != attempt_id:
        raise ContractError("Completed attempt lacks an accepted stored observation; recovery required")
    observations.read_one(store, job, reference, policy)
    return store.get(job["job_id"])

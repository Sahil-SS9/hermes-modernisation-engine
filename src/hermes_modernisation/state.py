"""Transactional attempt journal and worker fencing, never execution authority.

Only trusted controller code calls the lease/checkpoint methods. Public request
preparation is data-only. Expiry never transfers ownership or permits replay;
uncertain executions require inspection and explicit recovery.
"""

import hashlib
import hmac
import math
import secrets
import time
import uuid

from .jsonio import ContractError, dumps, loads, identifier
from .operations import AuthorityDenied, validate_operation

ACTIVE = {"RUNNING", "CLAIMED", "COLLECTED"}
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED", "RETIRED"}
TABLES = {"attempts", "observations", "reviews", "candidates"}


def install_schema(connection):
    statements = [
        "CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), request_id TEXT NOT NULL, input_hash TEXT NOT NULL, state TEXT NOT NULL, fence INTEGER NOT NULL, body BLOB NOT NULL, UNIQUE(job_id,request_id))",
        "CREATE UNIQUE INDEX IF NOT EXISTS one_active_attempt_per_job ON attempts(job_id) WHERE state IN ('RUNNING','CLAIMED','COLLECTED')",
        "CREATE TABLE IF NOT EXISTS observations (attempt_id TEXT PRIMARY KEY REFERENCES attempts(id), job_id TEXT NOT NULL REFERENCES jobs(id), phase TEXT NOT NULL, body BLOB NOT NULL, body_sha256 TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), purpose TEXT NOT NULL, body BLOB NOT NULL, body_sha256 TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), path TEXT UNIQUE NOT NULL, body BLOB NOT NULL, body_sha256 TEXT NOT NULL)",
    ]
    for statement in statements:
        connection.execute(statement)


def timestamp(value=None):
    value = time.time() if value is None else value
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError("Invalid trusted clock")
    return value


def _job(connection, job_id):
    identifier(job_id)
    row = connection.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        raise ContractError("Job not found in current profile")
    value = loads(row[0])
    if value.get("job_id") != job_id:
        raise ContractError("Stored job identity corrupted")
    return value


def _attempt(connection, job_id, attempt_id):
    identifier(attempt_id)
    row = connection.execute("SELECT job_id,state,fence,body FROM attempts WHERE id=?", (attempt_id,)).fetchone()
    if row is None or row[0] != job_id:
        raise ContractError("Attempt not found in current job/profile")
    value = loads(row[3])
    expected = {"schema_version", "kind", "job_id", "attempt_id", "request_id", "phase", "operation", "state", "fence", "permission_granted", "execution_performed", "failure_reason", "checkpoints", "_lease"}
    if set(value) != expected or type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "PreparedAttempt" or type(value["fence"]) is not int or value["fence"] < 0:
        raise ContractError("Stored attempt schema corrupted")
    if value["phase"] not in ("baseline", "candidate") or value["state"] not in ACTIVE | TERMINAL | {"PREPARED"} or any(type(value[key]) is not bool for key in ("permission_granted", "execution_performed")):
        raise ContractError("Stored attempt state corrupted")
    try:
        validate_operation(value["operation"])
    except AuthorityDenied as error:
        raise ContractError("Stored operation corrupted") from error
    if value["operation"]["job_id"] != job_id or value["operation"]["attempt_id"] != attempt_id:
        raise ContractError("Stored operation scope corrupted")
    if (value.get("job_id"), value.get("attempt_id"), value.get("state"), value.get("fence")) != (job_id, attempt_id, row[1], row[2]):
        raise ContractError("Stored attempt bindings corrupted")
    return value


def public_attempt(value):
    return {key: item for key, item in value.items() if not key.startswith("_")}


def _save(connection, job, attempt):
    connection.execute("UPDATE attempts SET state=?,fence=?,body=? WHERE id=? AND job_id=?", (attempt["state"], attempt["fence"], dumps(attempt), attempt["attempt_id"], job["job_id"]))
    job["revision"] += 1
    connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(job), job["job_id"]))


def prepare(store, job_id, request_id, blueprint, operation_factory):
    identifier(request_id)
    fingerprint = hashlib.sha256(dumps(blueprint)).hexdigest()
    with store.connection() as connection:
        job = _job(connection, job_id)
        if job.get("behaviour_contract", {}).get("digest") != blueprint["oracle_digest"]:
            raise ContractError("Protected contract changed before preparation")
        row = connection.execute("SELECT id,input_hash FROM attempts WHERE job_id=? AND request_id=?", (job_id, request_id)).fetchone()
        if row:
            if row[1] != fingerprint:
                raise ContractError("Idempotency key reused for changed preparation inputs")
            return public_attempt(_attempt(connection, job_id, row[0]))
        if job["state"] in {"CANCELLED", "FAILED", "INTERRUPTED", "HANDOFF_READY"}:
            raise ContractError("Job requires explicit recovery or a fresh job")
        aid = uuid.uuid4().hex
        operation = operation_factory(aid)
        if operation["job_id"] != job_id or operation["attempt_id"] != aid or operation["oracle_digest"] != blueprint["oracle_digest"]:
            raise ContractError("Trusted operation factory returned contradictory bindings")
        attempt = {
            "schema_version": 1, "kind": "PreparedAttempt", "job_id": job_id,
            "attempt_id": aid, "request_id": request_id, "phase": blueprint["phase"],
            "operation": operation, "state": "PREPARED", "fence": 0,
            "permission_granted": False, "execution_performed": False,
            "failure_reason": None, "checkpoints": [], "_lease": None,
        }
        connection.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?)", (aid, job_id, request_id, fingerprint, "PREPARED", 0, dumps(attempt)))
        job["revision"] += 1
        connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(job), job_id))
        return public_attempt(attempt)


def attempts_for(store, job_id):
    store.get(job_id)
    with store.read_connection() as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] < 4:
            return []
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='attempts' AND type='table'").fetchone():
            raise ContractError("Store schema corrupted: missing attempts")
        ids = connection.execute("SELECT id FROM attempts WHERE job_id=? ORDER BY rowid", (job_id,)).fetchall()
        return [public_attempt(_attempt(connection, job_id, row[0])) for row in ids]


def claim(store, job_id, attempt_id, worker, *, now=None, lease_seconds=900):
    now = timestamp(now)
    identifier(worker)
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 1800:
        raise ContractError("Invalid worker lease duration")
    with store.connection() as connection:
        job = _job(connection, job_id)
        attempt = _attempt(connection, job_id, attempt_id)
        active = connection.execute("SELECT id,body FROM attempts WHERE job_id=? AND state IN ('RUNNING','CLAIMED','COLLECTED')", (job_id,)).fetchone()
        if active:
            previous = _attempt(connection, job_id, active[0])
            if (previous.get("_lease") or {}).get("until", 0) <= now:
                raise ContractError("Expired ownership requires explicit runtime recovery; no replay")
            raise ContractError("Job already has an active claimed attempt")
        if attempt["state"] != "PREPARED":
            raise ContractError("Attempt requires recovery or is already terminal; no replay")
        if attempt["operation"]["oracle_digest"] != job.get("behaviour_contract", {}).get("digest"):
            raise ContractError("Prepared attempt is stale after protected contract change")
        if type(job.get("fence_epoch", 0)) is not int or job.get("fence_epoch", 0) < 0:
            raise ContractError("Stored job fencing epoch corrupted")
        token = secrets.token_hex(32)
        fence = job.get("fence_epoch", 0) + 1
        attempt.update(state="RUNNING", fence=fence, _lease={"worker": worker, "token_hash": hashlib.sha256(token.encode()).hexdigest(), "until": now + lease_seconds})
        job.update(fence_epoch=fence, state="BASELINE_RUNNING" if attempt["phase"] == "baseline" else "CANDIDATE_RUNNING")
        _save(connection, job, attempt)
        return {"fence": fence, "token": token, "worker": worker}


def _owned(job, attempt, lease, now):
    if type(lease) is not dict or set(lease) != {"fence", "token", "worker"} or type(lease["fence"]) is not int or type(lease["token"]) is not str:
        raise ContractError("Invalid fenced ownership capability")
    held = attempt.get("_lease")
    if attempt["state"] not in ACTIVE or not held or lease["fence"] != attempt["fence"] or lease["fence"] != job.get("fence_epoch") or held["worker"] != lease["worker"] or not hmac.compare_digest(held["token_hash"], hashlib.sha256(lease["token"].encode()).hexdigest()) or held["until"] <= now:
        raise ContractError("Stale fencing token or expired worker ownership; recovery required")


def checkpoint(store, job_id, attempt_id, lease, label, details, *, now=None):
    now = timestamp(now)
    if label not in {"AUTHORITY_CLAIMED", "START_REQUESTED", "COLLECTED", "CLEANUP_VERIFIED"}:
        raise ContractError("Unsupported execution checkpoint")
    raw = dumps(details)
    if len(raw) > 65536:
        raise ContractError("Checkpoint metadata budget exceeded")
    with store.connection() as connection:
        job = _job(connection, job_id)
        attempt = _attempt(connection, job_id, attempt_id)
        _owned(job, attempt, lease, now)
        labels = [entry["label"] for entry in attempt["checkpoints"]]
        expected = ["AUTHORITY_CLAIMED", "START_REQUESTED", "COLLECTED", "CLEANUP_VERIFIED"]
        if label in labels:
            previous = next(entry for entry in attempt["checkpoints"] if entry["label"] == label)
            if dumps(previous["details"]) != raw:
                raise ContractError("Checkpoint replay changed metadata")
            return public_attempt(attempt)
        if label != expected[len(labels)]:
            raise ContractError("Execution checkpoints must follow the declared order")
        attempt["checkpoints"].append({"label": label, "at": now, "details": loads(raw)})
        if label == "AUTHORITY_CLAIMED":
            attempt.update(state="CLAIMED", permission_granted=True)
        elif label == "COLLECTED":
            attempt["state"] = "COLLECTED"
            attempt["execution_performed"] = True
        _save(connection, job, attempt)
        return public_attempt(attempt)


def stop(store, job_id, attempt_id, lease, outcome, reason, *, now=None):
    now = timestamp(now)
    if outcome not in {"FAILED", "CANCELLED", "INTERRUPTED"} or type(reason) is not str or not 1 <= len(reason) <= 4000:
        raise ContractError("Explicit bounded interruption reason required")
    with store.connection() as connection:
        job = _job(connection, job_id)
        attempt = _attempt(connection, job_id, attempt_id)
        _owned(job, attempt, lease, now)
        job["fence_epoch"] += 1
        job["state"] = outcome
        attempt.update(state=outcome, failure_reason=reason, _lease=None)
        _save(connection, job, attempt)
        return public_attempt(attempt)

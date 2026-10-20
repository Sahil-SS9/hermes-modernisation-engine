"""Durable read-only-assessment jobs with idempotency and optimistic revisions.

This store cannot grant execution or promote evidence. Runtime receipts and
attempt fencing belong to the separate trusted executor, not caller JSON.
"""

import hashlib
import os
import sqlite3
import stat
import uuid
from contextlib import contextmanager, closing
import time
from pathlib import Path
from .jsonio import ContractError, dumps, loads, identifier


def partition_assessment(assessment):
    if type(assessment) is not dict:
        raise ContractError("Assessment must be an object")
    summary = dict(assessment)
    sections = {}
    blobs = {}
    total = 0
    for name in ("symbols", "dependencies", "rules"):
        if name in summary:
            sections[name] = summary.pop(name)
    if "source_manifest" in summary:
        manifest = dict(summary["source_manifest"])
        sections["files"] = manifest.pop("files")
        summary["source_manifest"] = manifest
    pages = {}
    counts = {}
    for name, items in sections.items():
        if type(items) is not list or len(items) > 20000:
            raise ContractError("Inventory section limit exceeded")
        counts[name] = len(items)
        pages[name] = []
        for start in range(0, len(items), 100):
            body = dumps({"items": items[start : start + 100]})
            total += len(body)
            if total > 33554432:
                raise ContractError("Inventory storage budget exceeded")
            digest = hashlib.sha256(body).hexdigest()
            blobs[digest] = body
            pages[name].append(digest)
    if sections:
        summary.update(detail_counts=counts, detail_pages=pages)
    dumps(summary)
    return summary, blobs


class Store:
    def __init__(self, root):
        self.root = Path(root)

    @contextmanager
    def read_connection(self):
        root = self.root
        path = root / "jobs.sqlite"
        if not root.is_absolute() or root.resolve() != root or not root.is_dir():
            raise ContractError("Private job store not found")
        info = root.stat()
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ContractError("Unsafe private job store")
        try:
            info = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_nlink != 1
                or info.st_mode & 0o077
            ):
                raise ContractError("Unsafe store file")
            with closing(
                sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
            ) as connection:
                if connection.execute("PRAGMA user_version").fetchone()[0] not in (
                    1,
                    2,
                    3,
                    4,
                ):
                    raise ContractError("Unsupported store schema")
                yield connection
        except (OSError, sqlite3.Error) as error:
            raise ContractError("Private job store unavailable") from error

    def migrate(self):
        with self.connection():
            pass

    @contextmanager
    def connection(self):
        root = self.root
        if not root.is_absolute():
            raise ContractError("Store path must be absolute")
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = root.stat()
        if (
            root.resolve() != root
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise ContractError("Store directory must be unambiguous and owner-only")
        path = root / "jobs.sqlite"
        try:
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(fd)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) & 0o077
                ):
                    raise ContractError("Unsafe store file")
            finally:
                os.close(fd)
            with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("BEGIN IMMEDIATE")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, 1, 2, 3, 4):
                    raise ContractError(
                        "Unsupported store schema; export/restore required"
                    )
                existing_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                required_tables = {"jobs"} if version else set()
                if version >= 2:
                    required_tables.add("details")
                if version >= 3:
                    required_tables.add("evaluations")
                if version == 4:
                    from .state import TABLES
                    required_tables.update(TABLES)
                    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='one_active_attempt_per_job'").fetchone():
                        raise ContractError("Store schema corrupted: attempt fencing index missing")
                if not required_tables <= existing_tables or (version == 0 and existing_tables):
                    raise ContractError("Store schema corrupted; no implicit repair")
                if version == 1:
                    self._backup(connection, "jobs.pre-v2.sqlite")
                if version == 2:
                    self._backup(connection, "jobs.pre-v3.sqlite")
                if version == 3:
                    self._backup(connection, "jobs.pre-v4.sqlite")
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL, body BLOB NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS details (hash TEXT PRIMARY KEY, body BLOB NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS evaluations (job_id TEXT NOT NULL, phase TEXT NOT NULL, source_digest TEXT NOT NULL, expectation_digest TEXT NOT NULL, body BLOB NOT NULL, body_sha256 TEXT NOT NULL, UNIQUE(job_id, phase))"
                )
                from .state import install_schema
                install_schema(connection)
                if version != 4:
                    connection.execute("PRAGMA user_version=4")
                yield connection
        except (OSError, sqlite3.Error) as error:
            raise ContractError(
                "Store unavailable; transaction not completed"
            ) from error

    def _backup(self, connection, name):
        root = self.root
        backup = root / name
        fd = os.open(
            backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
        )
        os.close(fd)
        deadline = time.monotonic() + 5

        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise ContractError("Backup deadline exceeded; upgrade not performed")

        path = root / "jobs.sqlite"
        with (
            closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as old,
            closing(sqlite3.connect(backup)) as saved,
        ):
            old.backup(saved, pages=128, progress=progress, sleep=0.05)
        fd = os.open(backup, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def create(self, request_id, repo, goal, assessment):
        identifier(request_id)
        if type(goal) is not str or not 1 <= len(goal) <= 4000:
            raise ContractError("Goal required, maximum 4000 characters")
        if type(repo) is not str or not Path(repo).is_absolute():
            raise ContractError("Absolute source path required")
        summary, blobs = partition_assessment(assessment)
        payload = {"repo": repo, "goal": goal, "assessment": summary}
        fingerprint = hashlib.sha256(dumps(payload)).hexdigest()
        with self.connection() as connection:
            row = connection.execute(
                "SELECT input_hash,body FROM jobs WHERE request=?", (request_id,)
            ).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise ContractError("Idempotency key reused for changed inputs")
                return loads(row[1])
            job = {
                "schema_version": 1,
                "kind": "AssessmentJob",
                "job_id": uuid.uuid4().hex,
                "revision": 0,
                "state": "ASSESSED",
                "plan": None,
                "repo": repo,
                "goal": goal,
                "assessment": summary,
                "execution_receipts": [],
                "execution_available": False,
            }
            for digest, body in blobs.items():
                connection.execute(
                    "INSERT OR IGNORE INTO details VALUES (?,?)", (digest, body)
                )
            connection.execute(
                "INSERT INTO jobs VALUES (?,?,?,?)",
                (job["job_id"], request_id, fingerprint, dumps(job)),
            )
            return job

    def get(self, job_id):
        identifier(job_id)
        with self.read_connection() as connection:
            row = connection.execute(
                "SELECT body FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise ContractError("Job not found in current profile")
            return loads(row[0])

    def details(self, job_id, section, page):
        if (
            section not in ("symbols", "dependencies", "rules", "files")
            or type(page) is not int
            or page < 0
        ):
            raise ContractError("Invalid inventory page")
        job = self.get(job_id)
        pages = job["assessment"].get("detail_pages", {}).get(section, [])
        if page >= len(pages):
            raise ContractError("Inventory page not found")
        digest = pages[page]
        with self.read_connection() as connection:
            row = connection.execute(
                "SELECT body FROM details WHERE hash=?", (digest,)
            ).fetchone()
            if row is None or hashlib.sha256(row[0]).hexdigest() != digest:
                raise ContractError("Missing or corrupted inventory shard")
            return {
                "section": section,
                "page": page,
                "items": loads(row[0])["items"],
                "has_more": page + 1 < len(pages),
                "sha256": digest,
            }

    def save_plan(self, job_id, revision, plan):
        identifier(job_id)
        if type(revision) is not int or revision < 0:
            raise ContractError("Expected revision required")
        dumps(plan)
        with self.connection() as connection:
            row = connection.execute(
                "SELECT body FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise ContractError("Job not found")
            job = loads(row[0])
            if job["revision"] != revision:
                raise ContractError("Stale job revision")
            if job["state"] not in ("ASSESSED", "BASELINE_AUTHORITY_REQUIRED"):
                raise ContractError("Planning unavailable in this state")
            job.update(
                revision=revision + 1, state="BASELINE_AUTHORITY_REQUIRED", plan=plan
            )
            connection.execute(
                "UPDATE jobs SET body=? WHERE id=?", (dumps(job), job_id)
            )
            return job

    def attempts_for(self, job_id):
        from .state import attempts_for
        return attempts_for(self, job_id)

    def claim_attempt(self, job_id, attempt_id, worker, *, now=None, lease_seconds=900):
        from .state import claim
        return claim(self, job_id, attempt_id, worker, now=now, lease_seconds=lease_seconds)

    def checkpoint_attempt(self, job_id, attempt_id, lease, label, details, *, now=None):
        from .state import checkpoint
        return checkpoint(self, job_id, attempt_id, lease, label, details, now=now)

    def stop_attempt(self, job_id, attempt_id, lease, outcome, reason, *, now=None):
        from .state import stop
        return stop(self, job_id, attempt_id, lease, outcome, reason, now=now)

    def save_contract(self, job_id, revision, contract):
        """Atomically retain unreviewed oracle bytes and their job-bound reference."""
        from .contracts import contract_summary

        identifier(job_id)
        if type(revision) is not int or revision < 0:
            raise ContractError("Expected revision required")
        raw = dumps(contract)
        summary = contract_summary(contract)
        with self.connection() as connection:
            row = connection.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise ContractError("Job not found in current profile")
            job = loads(row[0])
            if summary["source_digest"] != job["assessment"]["source_digest"]:
                raise ContractError("Contract source differs from assessed source")
            if job["revision"] != revision:
                if job["revision"] == revision + 1 and job.get("behaviour_contract") == summary:
                    return job
                raise ContractError("Stale job revision")
            if job["state"] not in ("ASSESSED", "BASELINE_AUTHORITY_REQUIRED"):
                raise ContractError("Contract changes unavailable after execution has begun")
            existing = connection.execute("SELECT body FROM details WHERE hash=?", (summary["digest"],)).fetchone()
            if existing is not None and existing[0] != raw:
                raise ContractError("Protected contract storage is corrupted")
            connection.execute("INSERT OR IGNORE INTO details VALUES (?,?)", (summary["digest"], raw))
            job.update(revision=revision + 1, state="BASELINE_AUTHORITY_REQUIRED", behaviour_contract=summary)
            connection.execute("UPDATE jobs SET body=? WHERE id=?", (dumps(job), job_id))
            return job

    def contract_for(self, job_id):
        """Trusted controller read; deliberately not exposed as a model/tool action."""
        from .contracts import contract_summary, validate_contract

        job = self.get(job_id)
        reference = job.get("behaviour_contract")
        if reference is None:
            raise ContractError("No protected behaviour contract registered")
        with self.read_connection() as connection:
            row = connection.execute("SELECT body FROM details WHERE hash=?", (reference["digest"],)).fetchone()
        if row is None or hashlib.sha256(row[0]).hexdigest() != reference["digest"]:
            raise ContractError("Protected contract missing or corrupted")
        value = validate_contract(loads(row[0]), job["repo"], job["assessment"]["source_digest"])
        if contract_summary(value) != reference or value["source_digest"] != job["assessment"]["source_digest"]:
            raise ContractError("Protected contract has contradictory job bindings")
        return value

    def record_evaluation(self, job_id, phase, source_digest, expectation, body):
        identifier(job_id)
        # Non-object bodies (list/str/number/null) never enter the evidence
        # table: the pairing and digest guarantees below assume object roots.
        if type(body) is not dict:
            raise ContractError("Evaluation body must be a JSON object")
        with self.connection() as connection:
            if not connection.execute(
                "SELECT 1 FROM jobs WHERE id=?", (job_id,)
            ).fetchone():
                raise ContractError("Job not found")
            if connection.execute(
                "SELECT 1 FROM evaluations WHERE job_id=? AND phase=?",
                (job_id, phase),
            ).fetchone():
                raise ContractError(f"Evidence already recorded for {phase} phase")
            pairs = connection.execute(
                "SELECT phase, expectation_digest FROM evaluations WHERE job_id=?",
                (job_id,),
            ).fetchall()
            for other_phase, other_digest in pairs:
                # Cross-phase mismatch must be caught at write time, inside the
                # same BEGIN IMMEDIATE transaction, so a divergent expectation
                # can never mix into one job's evidence pair. Nothing is written
                # on refusal; previously recorded evidence is retained.
                if other_digest != expectation["digest"]:
                    raise ContractError(
                        "Cross-phase expectation mismatch: the "
                        f"{other_phase} phase is already paired to a different "
                        f"expectation; refusing this {phase} write"
                    )
            raw = dumps(body)
            connection.execute(
                "INSERT INTO evaluations VALUES (?,?,?,?,?,?)",
                (
                    job_id,
                    phase,
                    source_digest,
                    expectation["digest"],
                    raw,
                    hashlib.sha256(raw).hexdigest(),
                ),
            )

    def evidence_for(self, job_id):
        identifier(job_id)
        # Deliberately read-only: compare/report consume evidence without
        # writes. Legacy v1/v2 stores have no evaluations table by design
        # (read_connection gates user_version to 1/2/3), so reading them must
        # return the empty gap report with NO schema change, migration or byte
        # difference. A version-3 store missing its table is corrupted, not
        # legacy: that refusal must carry its own distinct message.
        with self.read_connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version in (1, 2):
                return []
            if (
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='evaluations'"
                ).fetchone()
                is None
            ):
                raise ContractError(
                    "Store schema corrupted: version-3 store is missing the "
                    "evaluations table"
                )
            rows = connection.execute(
                "SELECT phase, source_digest, expectation_digest, body, body_sha256 FROM evaluations WHERE job_id=? ORDER BY rowid",
                (job_id,),
            ).fetchall()
        recorded = []
        for phase, source_digest, expectation_digest, body, body_sha256 in rows:
            if hashlib.sha256(body).hexdigest() != body_sha256:
                raise ContractError("Stored evidence corrupted")
            # jsonio.loads itself refuses non-object roots; re-style any stored
            # body refusal (including a sha-consistent non-object row) as this
            # seam's tamper error so compare/report never see a non-dict
            # evaluation.
            try:
                evaluation = loads(body)
            except ContractError as error:
                raise ContractError("Stored evidence corrupted; " + str(error)[:300]) from error
            if type(evaluation) is not dict:
                # Store-level invariant: must stay true even if the loads
                # contract ever changes (would otherwise reach comparison and
                # crash with AttributeError).
                raise ContractError("Stored evidence corrupted; not a JSON object")
            recorded.append(
                {
                    "phase": phase,
                    "source_digest": source_digest,
                    "expectation_digest": expectation_digest,
                    "evaluation": evaluation,
                }
            )
        return recorded

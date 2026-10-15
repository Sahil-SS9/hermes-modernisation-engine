"""Durable read-only-assessment jobs with idempotency and optimistic revisions.

This store cannot grant execution or promote evidence. Runtime receipts and
attempt fencing belong to the separate trusted executor, not caller JSON.
"""

import hashlib
import os
import re
import sqlite3
import stat
import uuid
from contextlib import contextmanager, closing
import time
from pathlib import Path
from .jsonio import ContractError, dumps, loads


def identifier(value):
    if type(value) is not str or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise ContractError("Invalid identifier")
    return value


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
                connection.execute("BEGIN IMMEDIATE")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, 1, 2):
                    raise ContractError(
                        "Unsupported store schema; export/restore required"
                    )
                if version == 1:
                    backup = root / "jobs.pre-v2.sqlite"
                    fd = os.open(
                        backup,
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                        0o600,
                    )
                    os.close(fd)
                    deadline = time.monotonic() + 5

                    def progress(status, remaining, total):
                        if time.monotonic() > deadline:
                            raise ContractError(
                                "Backup deadline exceeded; upgrade not performed"
                            )

                    with (
                        closing(
                            sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
                        ) as old,
                        closing(sqlite3.connect(backup)) as saved,
                    ):
                        old.backup(saved, pages=128, progress=progress, sleep=0.05)
                    fd = os.open(backup, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL, body BLOB NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS details (hash TEXT PRIMARY KEY, body BLOB NOT NULL)"
                )
                connection.execute("PRAGMA user_version=2")
                yield connection
        except (OSError, sqlite3.Error) as error:
            raise ContractError(
                "Store unavailable; transaction not completed"
            ) from error

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

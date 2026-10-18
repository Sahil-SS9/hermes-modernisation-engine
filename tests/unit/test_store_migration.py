import sqlite3

import pytest

from hermes_modernisation.jsonio import ContractError, dumps
from hermes_modernisation.store import Store


def test_v1_store_upgrades_without_dropping_original_job(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    path = root / "jobs.sqlite"
    original = {
        "schema_version": 1,
        "kind": "AssessmentJob",
        "job_id": "original",
        "revision": 0,
        "state": "ASSESSED",
        "assessment": {"source_digest": "a" * 64},
    }
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE jobs (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL, body BLOB NOT NULL)"
        )
        connection.execute(
            "INSERT INTO jobs VALUES (?,?,?,?)",
            ("original", "request", "hash", dumps(original)),
        )
        connection.execute("PRAGMA user_version=1")
    path.chmod(0o600)
    assert Store(root).get("original") == original
    Store(root).migrate()
    backup = root / "jobs.pre-v2.sqlite"
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute(
            "SELECT body FROM jobs WHERE id=?", ("original",)
        ).fetchone()[0] == dumps(original)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name='details'"
        ).fetchone()


def test_v2_store_upgrades_with_backup_and_no_loss(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    path = root / "jobs.sqlite"
    job = {"schema_version": 1, "kind": "AssessmentJob", "job_id": "v2"}
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE jobs (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL, body BLOB NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE details (hash TEXT PRIMARY KEY, body BLOB NOT NULL)"
        )
        connection.execute(
            "INSERT INTO jobs VALUES (?, 'q', 'h', ?)", ("v2", dumps(job))
        )
        connection.execute("INSERT INTO details VALUES ('d', ?)", (b"shard",))
        connection.execute("PRAGMA user_version=2")
    path.chmod(0o600)
    Store(root).migrate()
    backup = root / "jobs.pre-v3.sqlite"
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT body FROM jobs").fetchone()[0] == dumps(job)
        assert connection.execute("SELECT body FROM details").fetchone()[0] == b"shard"
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT body FROM jobs").fetchone()[0] == dumps(job)
        assert connection.execute("SELECT body FROM details").fetchone()[0] == b"shard"
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name='evaluations'"
        ).fetchone()
    assert Store(root).evidence_for("v2") == []


# --- round-2 corrections (implementer-owned) ---------------------------------


def test_malformed_v3_store_without_evaluations_fails_closed_distinctly(tmp_path):
    """A version-3 store missing its evaluations table must fail closed with a
    schema-corruption message, distinct from both the legacy gap report and the
    generic store-unavailable translation. Reading it changes no bytes."""
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    path = root / "jobs.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE jobs (id TEXT PRIMARY KEY, request TEXT UNIQUE NOT NULL, "
            "input_hash TEXT NOT NULL, body BLOB NOT NULL)"
        )
        connection.execute("PRAGMA user_version=3")
    path.chmod(0o600)
    before = path.read_bytes()
    with pytest.raises(ContractError, match="[Cc]orrupted"):
        Store(root).evidence_for("original")
    assert path.read_bytes() == before

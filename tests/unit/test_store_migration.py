import sqlite3
from hermes_modernisation.store import Store
from hermes_modernisation.jsonio import dumps


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
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name='details'"
        ).fetchone()

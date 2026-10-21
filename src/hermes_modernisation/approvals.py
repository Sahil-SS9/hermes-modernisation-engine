"""External-owner Ed25519 verification, with durable one-use claims.

Only public keys are accepted. No sign/approve operation exists. The trusted
operator must enrol keys and keep this ledger outside every candidate mount.
A claim is not evidence that code executed; lost attempts require recovery.
"""

from __future__ import annotations

import base64
import math
import os
import re
import sqlite3
import stat
import time
from contextlib import closing
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .operations import (
    AuthorityDenied as AuthorityDenied,
    canonical as canonical,
    validate_operation as validate_operation,
    OPERATION_FIELDS as OPERATION_FIELDS,
)


class ExternalAuthority:
    """Trusted executor dependency, never a model-writable approval API."""

    def __init__(self, public_keys: dict[str, bytes], ledger: Path, *, clock=time.time):
        self.public_keys = dict(public_keys)
        self.ledger = Path(ledger)
        self._clock = clock  # Trusted executor dependency; never a tool argument.

    def verify(self, grant: object, operation: dict):
        validate_operation(operation)
        return self._verify(grant, operation, "operation")

    def verify_review(self, grant, decision):
        from .reviews import validate_decision
        validate_decision(decision)
        return self._verify(grant, decision, "decision")

    def claim_review(self, grant, decision):
        nonce, now = self.verify_review(grant, decision)
        return self._record(decision, nonce, now)

    def claim(self, grant: object, operation: dict) -> str:
        nonce, now = self.verify(grant, operation)
        return self._record(operation, nonce, now)

    def verify_control(self, grant, decision):
        from .control import validate_decision
        validate_decision(decision)
        return self._verify(grant, decision, "decision")

    def verify_rule_review(self, grant, decision):
        from .rule_reviews import validate_decision
        validate_decision(decision)
        return self._verify(grant, decision, "decision")

    def claim_rule_review(self, grant, decision):
        nonce, now = self.verify_rule_review(grant, decision)
        return self._record(decision, nonce, now)

    def claim_control(self, grant, decision):
        nonce, now = self.verify_control(grant, decision)
        return self._record(decision, nonce, now)

    def verify_recorded(self, grant, payload, payload_field="operation"):
        """Read-only verification at the recorded claim time, not today's expiry.

        The private ledger is trusted executor state, never caller evidence.
        This keeps expired spent grants auditable without permitting reuse.
        """
        from .baseline import read_artifact
        if type(grant) is not dict or type(grant.get("body")) is not dict:
            raise AuthorityDenied("Missing recorded authority")
        body = grant["body"]
        nonce = body.get("nonce")
        if type(nonce) is not str:
            raise AuthorityDenied("Missing recorded authority nonce")
        # Enforce the same private single-file policy without creating a ledger.
        read_artifact(self.ledger, 16777216)
        try:
            with closing(sqlite3.connect(self.ledger.as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
                row = connection.execute("SELECT operation,claimed_at FROM claims WHERE actor=? AND nonce=?", (payload["actor"], nonce)).fetchone()
        except (OSError, sqlite3.Error) as error:
            raise AuthorityDenied("Recorded authority ledger unavailable") from error
        if row is None or row[0] != canonical(payload):
            raise AuthorityDenied("No authentic durable claim for this exact record")
        return self._verify(grant, payload, payload_field, at=row[1])

    def _verify(self, grant, operation, payload_field, *, at=None):
        now = self._clock() if at is None else at
        if type(grant) is not dict or set(grant) != {"body", "signature"}:
            raise AuthorityDenied("A signed external grant is required")
        body = grant["body"]
        if type(body) is not dict or set(body) != {
            "schema_version",
            payload_field,
            "nonce",
            "expires_at",
            "max_uses",
        }:
            raise AuthorityDenied("Unknown or missing grant fields")
        if (
            type(body["schema_version"]) is not int
            or body["schema_version"] != 1
            or type(body["max_uses"]) is not int
            or body["max_uses"] != 1
        ):
            raise AuthorityDenied("Only version 1 one-use grants are supported")
        if (
            type(now) not in (int, float)
            or not math.isfinite(now)
            or type(body["expires_at"]) not in (int, float)
            or not math.isfinite(body["expires_at"])
            or body["expires_at"] <= now
        ):
            raise AuthorityDenied("Expired or invalid grant clock")
        nonce = body["nonce"]
        if not isinstance(nonce, str) or not re.fullmatch(
            r"[a-zA-Z0-9_-]{8,128}", nonce
        ):
            raise AuthorityDenied("Invalid grant nonce")
        if canonical(body[payload_field]) != canonical(operation):
            raise AuthorityDenied("Operation differs from owner grant")
        try:
            key = self.public_keys[operation["actor"]]
            signature = base64.b64decode(grant["signature"], validate=True)
            Ed25519PublicKey.from_public_bytes(key).verify(signature, canonical(body))
        except (KeyError, ValueError, TypeError, InvalidSignature) as error:
            raise AuthorityDenied("Unenrolled owner or invalid signature") from error
        return nonce, now

    def _record(self, operation, nonce, now):
        parent = self.ledger.parent
        if (
            not self.ledger.is_absolute()
            or parent.resolve() != parent
            or not parent.is_dir()
        ):
            raise AuthorityDenied(
                "Ledger requires an existing unambiguous private directory"
            )
        info = parent.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise AuthorityDenied("Ledger directory must be owner-only")
        try:
            descriptor = os.open(
                self.ledger, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
            )
            try:
                info = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) & 0o077
                ):
                    raise AuthorityDenied("Unsafe ledger file")
            finally:
                os.close(descriptor)
            with (
                closing(sqlite3.connect(self.ledger, timeout=5)) as connection,
                connection,
            ):
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS claims (actor TEXT NOT NULL, nonce TEXT NOT NULL, operation BLOB NOT NULL, claimed_at REAL NOT NULL, PRIMARY KEY(actor, nonce))"
                )
                connection.execute(
                    "INSERT INTO claims VALUES (?, ?, ?, ?)",
                    (operation["actor"], nonce, canonical(operation), now),
                )
        except (OSError, sqlite3.Error) as error:
            raise AuthorityDenied(
                "Grant already consumed or ledger unavailable"
            ) from error
        return nonce

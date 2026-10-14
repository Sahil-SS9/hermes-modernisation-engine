"""External-owner Ed25519 verification, with durable one-use claims.

Only public keys are accepted. No sign/approve operation exists. The trusted
operator must enrol keys and keep this ledger outside every candidate mount.
A claim is not evidence that code executed; lost attempts require recovery.
"""
from __future__ import annotations

import base64
import json
import math
import os
import re
import sqlite3
import stat
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

OPERATION_FIELDS = {
    'schema_version', 'job_id', 'attempt_id', 'actor', 'profile',
    'source_digest', 'candidate_digest', 'oracle_digest', 'environment_digest',
    'image_digest', 'argv', 'read_roots', 'write_roots', 'network',
    'timeout_seconds', 'output_limit_bytes',
}


class AuthorityDenied(PermissionError):
    """No authentic authority for the exact requested operation."""


def canonical(value: dict) -> bytes:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (TypeError, ValueError, RecursionError) as error:
        raise AuthorityDenied('Invalid grant encoding') from error
    if len(raw) > 65536:
        raise AuthorityDenied('Grant exceeds 64 KiB')
    return raw


def validate_operation(operation: dict) -> None:
    if type(operation) is not dict or set(operation) != OPERATION_FIELDS:
        raise AuthorityDenied('Unknown or missing operation fields')
    if type(operation['schema_version']) is not int or operation['schema_version'] != 1:
        raise AuthorityDenied('Unsupported operation version')
    for field in ('job_id', 'attempt_id', 'actor', 'profile'):
        if not isinstance(operation[field], str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', operation[field]):
            raise AuthorityDenied('Invalid operation identifier')
    for field in ('source_digest', 'candidate_digest', 'oracle_digest', 'environment_digest', 'image_digest'):
        if not isinstance(operation[field], str) or not re.fullmatch(r'[a-f0-9]{64}', operation[field]):
            raise AuthorityDenied('Invalid operation digest')
    if operation['network'] != 'none' or operation['read_roots'] != ['/source'] or operation['write_roots'] != ['/tmp', '/work']:
        raise AuthorityDenied('Unsupported sandbox scope')
    argv = operation['argv']
    if type(argv) is not list or not 1 <= len(argv) <= 128 or any(not isinstance(arg, str) or chr(0) in arg or len(arg) > 16384 for arg in argv):
        raise AuthorityDenied('Invalid command argv')
    for field, maximum in (('timeout_seconds', 600), ('output_limit_bytes', 4194304)):
        if type(operation[field]) is not int or not 1 <= operation[field] <= maximum:
            raise AuthorityDenied('Invalid resource bound')


class ExternalAuthority:
    """Trusted executor dependency, never a model-writable approval API."""

    def __init__(self, public_keys: dict[str, bytes], ledger: Path, *, clock=time.time):
        self.public_keys = dict(public_keys)
        self.ledger = Path(ledger)
        self._clock = clock  # Trusted executor dependency; never a tool argument.

    def claim(self, grant: object, operation: dict) -> str:
        now = self._clock()
        validate_operation(operation)
        if type(grant) is not dict or set(grant) != {'body', 'signature'}:
            raise AuthorityDenied('A signed external grant is required')
        body = grant['body']
        if type(body) is not dict or set(body) != {'schema_version', 'operation', 'nonce', 'expires_at', 'max_uses'}:
            raise AuthorityDenied('Unknown or missing grant fields')
        if type(body['schema_version']) is not int or body['schema_version'] != 1 or type(body['max_uses']) is not int or body['max_uses'] != 1:
            raise AuthorityDenied('Only version 1 one-use grants are supported')
        if type(now) not in (int, float) or not math.isfinite(now) or type(body['expires_at']) not in (int, float) or not math.isfinite(body['expires_at']) or body['expires_at'] <= now:
            raise AuthorityDenied('Expired or invalid grant clock')
        nonce = body['nonce']
        if not isinstance(nonce, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}', nonce):
            raise AuthorityDenied('Invalid grant nonce')
        validate_operation(body['operation'])
        if canonical(body['operation']) != canonical(operation):
            raise AuthorityDenied('Operation differs from owner grant')
        try:
            key = self.public_keys[operation['actor']]
            signature = base64.b64decode(grant['signature'], validate=True)
            Ed25519PublicKey.from_public_bytes(key).verify(signature, canonical(body))
        except (KeyError, ValueError, TypeError, InvalidSignature) as error:
            raise AuthorityDenied('Unenrolled owner or invalid signature') from error
        parent = self.ledger.parent
        if not self.ledger.is_absolute() or parent.resolve() != parent or not parent.is_dir():
            raise AuthorityDenied('Ledger requires an existing unambiguous private directory')
        info = parent.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise AuthorityDenied('Ledger directory must be owner-only')
        try:
            descriptor = os.open(self.ledger, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                    raise AuthorityDenied('Unsafe ledger file')
            finally:
                os.close(descriptor)
            with sqlite3.connect(self.ledger, timeout=5) as connection:
                connection.execute('PRAGMA synchronous=FULL')
                connection.execute('BEGIN IMMEDIATE')
                connection.execute('CREATE TABLE IF NOT EXISTS claims (actor TEXT NOT NULL, nonce TEXT NOT NULL, operation BLOB NOT NULL, claimed_at REAL NOT NULL, PRIMARY KEY(actor, nonce))')
                connection.execute('INSERT INTO claims VALUES (?, ?, ?, ?)', (operation['actor'], nonce, canonical(operation), now))
        except (OSError, sqlite3.Error) as error:
            raise AuthorityDenied('Grant already consumed or ledger unavailable') from error
        return nonce

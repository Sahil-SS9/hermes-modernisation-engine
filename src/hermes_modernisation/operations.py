"""Host-neutral exact operation schema and canonical signed encoding."""

import json
import re

OPERATION_FIELDS = {
    "schema_version",
    "job_id",
    "attempt_id",
    "actor",
    "profile",
    "source_digest",
    "candidate_digest",
    "oracle_digest",
    "environment_digest",
    "image_digest",
    "argv",
    "read_roots",
    "write_roots",
    "network",
    "timeout_seconds",
    "output_limit_bytes",
}


class AuthorityDenied(PermissionError):
    """No authentic authority for the exact requested operation."""


def canonical(value: dict) -> bytes:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    except (TypeError, ValueError, RecursionError) as error:
        raise AuthorityDenied("Invalid grant encoding") from error
    if len(raw) > 65536:
        raise AuthorityDenied("Grant exceeds 64 KiB")
    return raw


def validate_operation(operation: dict) -> None:
    if type(operation) is not dict or set(operation) != OPERATION_FIELDS:
        raise AuthorityDenied("Unknown or missing operation fields")
    if type(operation["schema_version"]) is not int or operation["schema_version"] != 1:
        raise AuthorityDenied("Unsupported operation version")
    for field in ("job_id", "attempt_id", "actor", "profile"):
        if not isinstance(operation[field], str) or not re.fullmatch(
            r"[a-zA-Z0-9_-]{1,80}", operation[field]
        ):
            raise AuthorityDenied("Invalid operation identifier")
    for field in (
        "source_digest",
        "candidate_digest",
        "oracle_digest",
        "environment_digest",
        "image_digest",
    ):
        if not isinstance(operation[field], str) or not re.fullmatch(
            r"[a-f0-9]{64}", operation[field]
        ):
            raise AuthorityDenied("Invalid operation digest")
    if (
        operation["network"] != "none"
        or operation["read_roots"] != ["/source"]
        or operation["write_roots"] != ["/tmp", "/work"]
    ):
        raise AuthorityDenied("Unsupported sandbox scope")
    argv = operation["argv"]
    if (
        type(argv) is not list
        or not 1 <= len(argv) <= 128
        or any(
            not isinstance(arg, str) or chr(0) in arg or len(arg) > 16384
            for arg in argv
        )
    ):
        raise AuthorityDenied("Invalid command argv")
    for field, maximum in (("timeout_seconds", 600), ("output_limit_bytes", 4194304)):
        if type(operation[field]) is not int or not 1 <= operation[field] <= maximum:
            raise AuthorityDenied("Invalid resource bound")



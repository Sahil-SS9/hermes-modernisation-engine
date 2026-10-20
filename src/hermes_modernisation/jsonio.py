"""Bounded, duplicate-free, canonical JSON for local versioned contracts."""

import json
import math
import re

MAX_BYTES = 1048576
MAX_DEPTH = 24
MAX_NODES = 20000


class ContractError(ValueError):
    """Unusable or ambiguous product data."""


def identifier(value):
    if type(value) is not str or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise ContractError("Invalid identifier")
    return value


def _validate(value, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    if depth > MAX_DEPTH or count[0] > MAX_NODES:
        raise ContractError("JSON depth/node limit exceeded")
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ContractError("JSON keys must be strings")
            key.encode("utf-8")
            _validate(child, depth + 1, count)
    elif type(value) is list:
        for child in value:
            _validate(child, depth + 1, count)
    elif type(value) is str:
        value.encode("utf-8")
    elif type(value) is int:
        if abs(value) > 9007199254740991:
            raise ContractError("Integer outside portable JSON range")
    elif type(value) is float:
        if not math.isfinite(value):
            raise ContractError("Nonfinite number")
    elif value is not None and type(value) is not bool:
        raise ContractError("Unsupported JSON type")


def dumps(value):
    try:
        if type(value) is not dict:
            raise ContractError("Contract root must be an object")
        _validate(value)
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise ContractError("JSON byte limit exceeded")
        return raw
    except (UnicodeError, TypeError, ValueError, RecursionError) as error:
        raise ContractError(str(error)) from error


def loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError("Duplicate object key")
            result[key] = value
        return result

    try:
        if type(raw) is str:
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            raise ContractError("JSON input type/size refused")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ContractError("Nonfinite constant")
            ),
        )
        dumps(value)
        return value
    except (UnicodeError, TypeError, ValueError, RecursionError) as error:
        raise ContractError(str(error)) from error

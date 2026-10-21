"""Typed, narrow, contract-sealed output normalisations.

Only a reviewed behaviour contract can authorise a difference.  There is no
regex, expression, script, wildcard or partial masking: each entry names one
case and one or more object-field operations.  Missing fields fail closed at
evaluation time rather than silently hiding a difference.
"""

from .jsonio import ContractError, dumps, identifier, loads

ENTRY_FIELDS = {"case_id", "operations"}
LEAF_OPS = {"trim", "lowercase", "drop"}
ROUND = "round"
FIELD = r"[A-Za-z0-9_-]{1,64}"


def _path(value):
    if (
        type(value) is not str
        or not 1 <= len(value) <= 260
        or value.count(".") > 3
    ):
        raise ContractError("Narrow dotted output path required")
    parts = value.split(".")
    if any(not part or len(part) > 64 for part in parts):
        raise ContractError("Narrow dotted output path required")
    for part in parts:
        if not all(char.isalnum() or char in "_-" for char in part):
            raise ContractError("Only literal object-field names are supported")
    return parts


def validate_approved(value):
    """Validate comparison-disclosed operations without a contract at hand."""
    if type(value) is not list or len(value) > 20:
        raise ContractError("Bounded approved differences required")
    identifiers = set()
    for entry in value:
        if type(entry) is not dict or set(entry) != ENTRY_FIELDS:
            raise ContractError("Unsupported approved-difference fields")
        identifier(entry["case_id"])
        if entry["case_id"] in identifiers:
            raise ContractError("Duplicate approved-difference case")
        identifiers.add(entry["case_id"])
    return validate_entries(value, identifiers)


def validate_entries(value, case_ids):
    if type(value) is not list or len(value) > 20:
        raise ContractError("Bounded normalisation entries required")
    seen_cases = set()
    for entry in value:
        if type(entry) is not dict or set(entry) != ENTRY_FIELDS:
            raise ContractError("Unsupported normalisation entry fields")
        case_id = identifier(entry["case_id"])
        if case_id not in case_ids or case_id in seen_cases:
            raise ContractError("Normalisation case is absent or duplicated")
        seen_cases.add(case_id)
        operations = entry["operations"]
        if type(operations) is not list or not 1 <= len(operations) <= 10:
            raise ContractError("Bounded normalisation operations required")
        seen_paths = set()
        for operation in operations:
            if type(operation) is not dict:
                raise ContractError("Normalisation operation must be typed data")
            op = operation.get("op")
            if op in LEAF_OPS:
                if set(operation) != {"op", "path"}:
                    raise ContractError("Unsupported leaf normalisation fields")
            elif op == ROUND:
                if set(operation) != {"op", "path", "digits"}:
                    raise ContractError("Unsupported round normalisation fields")
                digits = operation["digits"]
                if type(digits) is not int or not 0 <= digits <= 6:
                    raise ContractError("Round digits must be 0..6")
            else:
                raise ContractError("Unsupported normalisation operation")
            path = ".".join(_path(operation["path"]))
            if path in seen_paths:
                raise ContractError("Overlapping normalisation paths refused")
            seen_paths.add(path)
    return value


def entries(contract):
    value = contract.get("normalizations")
    if value is None:
        return []
    return value


def _locate(target, path, *, create=False):
    parts = _path(path)
    current = target
    for part in parts[:-1]:
        if type(current) is not dict or part not in current:
            raise ContractError("Normalisation path is absent from the response")
        current = current[part]
        if type(current) is not dict:
            raise ContractError("Normalisation path crosses a non-object value")
    if type(current) is not dict or (parts[-1] not in current and not create):
        raise ContractError("Normalisation path is absent from the response")
    return current, parts[-1]


def apply_to_case(contract, case_id, value):
    """Return a deep-copied normalised value and the exact operations applied."""
    matching = [entry for entry in entries(contract) if entry["case_id"] == case_id]
    if not matching:
        return value, []
    copied = loads(dumps({"value": value}))["value"]
    applied = []
    for operation in matching[0]["operations"]:
        op = operation["op"]
        path = operation["path"]
        if op == "drop":
            parent, key = _locate(copied, path)
            del parent[key]
        elif op in {"trim", "lowercase"}:
            parent, key = _locate(copied, path)
            current = parent[key]
            if type(current) is not str:
                raise ContractError("String normalisation requires a string field")
            parent[key] = current.strip() if op == "trim" else current.lower()
        elif op == "round":
            parent, key = _locate(copied, path)
            current = parent[key]
            if type(current) not in (int, float) or type(current) is bool:
                raise ContractError("Round normalisation requires a number")
            parent[key] = round(current, operation["digits"])
        applied.append(dict(operation))
    return copied, applied


def matches(contract, case_id, output, expected):
    normalised_output, applied = apply_to_case(contract, case_id, output)
    normalised_expected, _ = apply_to_case(contract, case_id, expected)
    return dumps({"value": normalised_output}) == dumps({"value": normalised_expected}), applied


def approved_difference(contract, case_id):
    matching = [entry for entry in entries(contract) if entry["case_id"] == case_id]
    if not matching:
        return None
    return {"case_id": case_id, "operations": [dict(op) for op in matching[0]["operations"]]}

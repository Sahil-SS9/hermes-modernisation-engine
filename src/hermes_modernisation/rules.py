"""Strict BusinessRule v1 lexical candidates; never mint review or coverage.

The candidate-only state is deliberate. Reviewed rules and executed case links
must be derived later from authenticated decisions and protected observations,
not from edits to a lexical inventory page. Source text is not copied out.
"""

import hashlib

from .contracts import bounded_text, digest, fields
from .identity import safe_relative
from .jsonio import ContractError, dumps, identifier

SCHEMA_NAME = "business-rule-v1"
MAX_LINE = 2147483647
FACTS = {
    "kind": "BusinessRule", "origin": "assertion-location-candidate",
    "review_state": "unreviewed", "owner_reviewed": False,
    "coverage_status": "unverified", "assertion_adequacy": "unknown",
}
FIELDS = {"schema_version", "id", "source_digest", "path", "line", "source_sha256", "source_refs", "text", "case_ids", "assertion_ids", "unknowns", *FACTS}


def rule_id(path, line):
    return "rule-" + hashlib.sha256((path + ":" + str(line)).encode()).hexdigest()[:16]


def validate_rule(value, source_digest):
    dumps(value)
    fields(value, FIELDS, "BusinessRule")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported BusinessRule version")
    for key, expected in FACTS.items():
        if type(value[key]) is not type(expected) or value[key] != expected:
            raise ContractError("Lexical rule cannot assert review, adequacy or executed coverage")
    if digest(value["source_digest"]) != digest(source_digest):
        raise ContractError("BusinessRule source differs from its assessment")
    path = safe_relative(value["path"])
    line = value["line"]
    if type(line) is not int or not 1 <= line <= MAX_LINE:
        raise ContractError("Invalid rule citation integer")
    identifier(value["id"])
    if value["id"] != rule_id(path, line):
        raise ContractError("BusinessRule stable id contradicts its citation")
    sha = digest(value["source_sha256"])
    bounded_text(value["text"], 4000, "rule text")
    refs = value["source_refs"]
    if type(refs) is not list or len(refs) != 1:
        raise ContractError("One exact lexical rule citation is required")
    ref = refs[0]
    fields(ref, {"path", "line_start", "line_end", "sha256"}, "rule citation")
    safe_relative(ref["path"])
    digest(ref["sha256"])
    if any(type(ref[key]) is not int for key in ("line_start", "line_end")) or not 1 <= ref["line_start"] <= ref["line_end"] <= MAX_LINE:
        raise ContractError("Invalid rule citation line range")
    if (ref["path"], ref["line_start"], ref["sha256"]) != (path, line, sha):
        raise ContractError("BusinessRule source citation fields contradict each other")
    for key in ("case_ids", "assertion_ids"):
        if type(value[key]) is not list or value[key] != []:
            raise ContractError("Lexical rule cannot manufacture protected case/assertion links")
    unknowns = value["unknowns"]
    if type(unknowns) is not list or not 1 <= len(unknowns) <= 20:
        raise ContractError("BusinessRule unknowns must remain explicit")
    for unknown in unknowns:
        bounded_text(unknown, 4000, "rule unknown")
    if len(set(unknowns)) != len(unknowns):
        raise ContractError("Duplicate BusinessRule unknown")
    return value


def candidate(path, line, end_line, sha, source_digest):
    return validate_rule({
        "schema_version": 1, **FACTS, "id": rule_id(path, line),
        "source_digest": source_digest, "path": path, "line": line,
        "source_sha256": sha,
        "source_refs": [{"path": path, "line_start": line, "line_end": end_line, "sha256": sha}],
        "text": "Unreviewed assertion-location candidate; inspect the cited source before defining a behavioural rule.",
        "case_ids": [], "assertion_ids": [],
        "unknowns": ["Lexical extraction is not a complete business-rule inventory", "Owner review, oracle linkage, executed coverage and assertion adequacy are unverified"],
    }, source_digest)


def rule_schema():
    """Candidate-only schema; cross-field source/id consistency is also enforced."""
    sha = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    path = {"type": "string", "minLength": 1, "format": "relative-source-path"}
    line = {"type": "integer", "minimum": 1, "maximum": MAX_LINE}
    props = {
        "schema_version": {"type": "integer", "const": 1},
        **{name: {"const": value} for name, value in FACTS.items()},
        "id": {"type": "string", "pattern": "^rule-[a-f0-9]{16}$"},
        "source_digest": sha, "path": path, "line": line, "source_sha256": sha,
        "source_refs": {"type": "array", "minItems": 1, "maxItems": 1, "items": {"type": "object", "required": ["path", "line_start", "line_end", "sha256"], "additionalProperties": False, "properties": {"path": path, "line_start": line, "line_end": line, "sha256": sha}}},
        "text": {"type": "string", "minLength": 1, "maxLength": 4000},
        "case_ids": {"type": "array", "const": []},
        "assertion_ids": {"type": "array", "const": []},
        "unknowns": {"type": "array", "minItems": 1, "maxItems": 20, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 4000}},
    }
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:hermes-modernisation:business-rule:v1", "title": "BusinessRule v1 lexical candidate", "$comment": "Candidate-only contract; no owner review, oracle linkage or executed coverage is inferred. Core validation also rejects bool/integer coercion, unsafe paths and contradictory source/citation/id fields. Legacy unversioned inventory rows remain legacy and are never executed as a current rule.", "type": "object", "additionalProperties": False, "required": ["schema_version", "id", "source_digest", "path", "line", "source_sha256", "source_refs", "text", "case_ids", "assertion_ids", "unknowns", *FACTS], "properties": props}

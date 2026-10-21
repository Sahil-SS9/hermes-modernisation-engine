"""Strict protected response contracts; data registration never grants authority.

Expected values live in private engine storage, not in app mounts or proposer
context. A reviewed contract is a separate authenticated decision: these bytes
cannot label themselves reviewed, adequate or observed.
"""

import hashlib
import re
from pathlib import Path

from .identity import read_source, safe_relative, snapshot
from .jsonio import ContractError, dumps, loads, identifier
from .proposals import PROTECTED

CONTRACT_FIELDS = {
    "schema_version", "kind", "scope", "track", "source_digest", "adapter",
    "runtimes", "allowed_paths", "seed", "rules", "cases", "normalizations",
    "planned_differences",
}


def fields(value, names, label):
    if type(value) is not dict or set(value) != set(names):
        raise ContractError(f"Unknown or missing {label} fields")


def digest(value):
    if type(value) is not str or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ContractError("A full lowercase SHA-256 digest is required")
    return value


def bounded_text(value, maximum, label):
    if type(value) is not str or not 1 <= len(value) <= maximum:
        raise ContractError(f"Invalid bounded {label}")
    return value


def input_digest(value):
    return hashlib.sha256(dumps({"input": value})).hexdigest()


def validate_contract(value, source, source_digest):
    value = loads(dumps(value))
    fields(value, CONTRACT_FIELDS, "behaviour contract")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported behaviour contract version")
    if value["kind"] != "BehaviourContract" or value["adapter"] != "json-batch-v1":
        raise ContractError("Unsupported behaviour contract kind or adapter")
    identifier(value["scope"])
    if value["track"] not in ("uplift", "transform", "reimagine"):
        raise ContractError("Unsupported migration track")
    if digest(value["source_digest"]) != digest(source_digest):
        raise ContractError("Contract source differs from assessed source")
    source = Path(source)
    if snapshot(source)["digest"] != source_digest:
        raise ContractError("Contract source identity is stale")
    if type(value["seed"]) is not int or not 0 <= value["seed"] <= 2147483647:
        raise ContractError("Bounded deterministic seed required")
    fields(value["runtimes"], {"baseline", "candidate"}, "runtime pair")
    for runtime in value["runtimes"].values():
        fields(runtime, {"image", "argv"}, "runtime")
        if type(runtime["image"]) is not str or not re.fullmatch(
            r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}", runtime["image"]
        ):
            raise ContractError("Runtime image must be pinned by digest")
        argv = runtime["argv"]
        if type(argv) is not list or not 1 <= len(argv) <= 128 or any(
            type(arg) is not str or "\0" in arg or len(arg) > 16384 for arg in argv
        ):
            raise ContractError("Bounded literal command argv required")
    paths = value["allowed_paths"]
    if type(paths) is not list or not 1 <= len(paths) <= 100:
        raise ContractError("Bounded allowed paths required")
    for path in paths:
        safe_relative(path)
        if any(part in PROTECTED or part.startswith(".") for part in Path(path).parts) or Path(path).name.startswith("test_"):
            raise ContractError("Protected oracle/test paths cannot be candidate outputs")
    if len(set(paths)) != len(paths):
        raise ContractError("Duplicate allowed path")
    rules = value["rules"]
    cases = value["cases"]
    if type(rules) is not list or not 1 <= len(rules) <= 100:
        raise ContractError("Bounded explicitly cited rules required")
    if type(cases) is not list or not 12 <= len(cases) <= 500:
        raise ContractError("Ten fresh plus boundary/malformed cases required")
    rule_index = {}
    for rule in rules:
        fields(rule, {"id", "text", "source_refs", "case_ids"}, "business rule")
        rid = identifier(rule["id"])
        if rid in rule_index:
            raise ContractError("Duplicate rule identity")
        bounded_text(rule["text"], 4000, "rule text")
        refs = rule["source_refs"]
        if type(refs) is not list or not 1 <= len(refs) <= 20:
            raise ContractError("Rule source citations required")
        for ref in refs:
            fields(ref, {"path", "line_start", "line_end", "sha256"}, "source citation")
            raw, _ = read_source(source, safe_relative(ref["path"]))
            if hashlib.sha256(raw).hexdigest() != digest(ref["sha256"]):
                raise ContractError("Rule source citation bytes changed")
            if any(type(ref[key]) is not int for key in ("line_start", "line_end")) or not 1 <= ref["line_start"] <= ref["line_end"] <= len(raw.splitlines()):
                raise ContractError("Rule source citation lines out of bounds")
        ids = rule["case_ids"]
        if type(ids) is not list or not ids or any(type(x) is not str for x in ids) or len(set(ids)) != len(ids):
            raise ContractError("Distinct linked rule cases required")
        rule_index[rid] = set(ids)
    case_index = {}
    fresh = set()
    kinds = set()
    for case in cases:
        fields(case, {"id", "kind", "input", "expected", "rule_ids"}, "oracle case")
        cid = identifier(case["id"])
        if cid in case_index:
            raise ContractError("Duplicate case identity")
        if type(case["kind"]) is not str or case["kind"] not in {"fresh", "boundary", "malformed", "state", "property", "metamorphic", "concurrency"}:
            raise ContractError("Unsupported case kind")
        links = case["rule_ids"]
        if type(links) is not list or not links or any(type(x) is not str for x in links) or len(set(links)) != len(links):
            raise ContractError("Distinct case rule links required")
        for rid in links:
            if rid not in rule_index or cid not in rule_index[rid]:
                raise ContractError("Case/rule linkage is missing or contradictory")
        case_index[cid] = set(links)
        kinds.add(case["kind"])
        if case["kind"] == "fresh":
            fresh.add(input_digest(case["input"]))
    for rid, ids in rule_index.items():
        if any(cid not in case_index or rid not in case_index[cid] for cid in ids):
            raise ContractError("Rule references missing or contradictory cases")
    if len(fresh) < 10 or not {"boundary", "malformed"} <= kinds:
        raise ContractError("Ten distinct fresh inputs plus boundary/malformed cases required")
    from .differences import validate_entries
    if value["planned_differences"] != []:
        raise ContractError(
            "Planned behavioural differences remain unavailable; only typed narrow normalisations are supported"
        )
    validate_entries(value["normalizations"], set(case_index))
    if snapshot(source)["digest"] != source_digest:
        raise ContractError("Source changed while validating protected contract")
    return value


def contract_summary(value):
    return {
        "schema_version": 1,
        "kind": "BehaviourContractReference",
        "digest": hashlib.sha256(dumps(value)).hexdigest(),
        "source_digest": value["source_digest"],
        "scope": value["scope"],
        "track": value["track"],
        "adapter": value["adapter"],
        "case_count": len(value["cases"]),
        "fresh_count": sum(case["kind"] == "fresh" for case in value["cases"]),
        "rule_count": len(value["rules"]),
        "review_state": "unreviewed",
        "adequacy": "unverified",
    }

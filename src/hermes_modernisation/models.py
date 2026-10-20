"""Strict current MigrationJob headers, with an explicit legacy record boundary.

Private legacy AssessmentJob records remain readable without rewriting their
bytes or pretending that they contain a complete migration contract. Current
public jobs bind their profile, identity, state and disabled model policy.
Execution observations/reviews still require their separate authenticated reads.
"""

from pathlib import Path

from .contracts import digest, fields
from .jsonio import ContractError, dumps, identifier

BASE_FIELDS = {"schema_version", "kind", "job_id", "revision", "state", "plan", "repo", "goal", "assessment", "execution_receipts", "execution_available"}
MIGRATION_FIELDS = {"profile", "track", "adapter_version", "supported_behaviours", "input_split", "budget", "model_policy", "allowed_output_roots"}
OPTIONAL_FIELDS = {"behaviour_contract", "baseline_ref", "candidate_observation_ref", "candidate_ref", "contract_review", "migration_review", "proposal_ref", "candidate_reservation", "fence_epoch", "failure_reason", "cancel_ref", "recovery_ref", "build_recovery_ref"}
STATES = {"CREATED", "ASSESSED", "BASELINE_AUTHORITY_REQUIRED", "BASELINE_AUTHORITY_GRANTED", "BASELINE_RUNNING", "BASELINED", "PLAN_REVIEW_REQUIRED", "MIGRATION_APPROVED", "CANDIDATE_BUILDING", "CANDIDATE_BUILT", "CANDIDATE_AUTHORITY_REQUIRED", "CANDIDATE_RUNNING", "VERIFIED", "HANDOFF_READY", "BLOCKED_PREREQUISITE", "EXECUTION_UNAVAILABLE", "AUTHORITY_REQUIRED", "INTERRUPTED", "BUDGET_STOPPED", "FAILED", "CANCELLED", "RECOVERY_REQUIRED"}
KINDS = ("fresh", "boundary", "malformed", "state", "property", "metamorphic", "concurrency")
BUDGET_FIELDS = {"model_calls_limit", "model_tokens_limit", "wall_seconds_limit", "output_bytes_limit", "model_calls_used", "model_tokens_used", "actual_cost"}


def metadata(profile):
    identifier(profile)
    return {"profile": profile, "track": None, "adapter_version": None,
            "supported_behaviours": [], "input_split": {"seed": None, **dict.fromkeys(KINDS, 0)},
            "budget": {"model_calls_limit": 0, "model_tokens_limit": 0, "wall_seconds_limit": 0, "output_bytes_limit": 0, "model_calls_used": 0, "model_tokens_used": None, "actual_cost": None},
            "model_policy": {"enabled": False, "egress_allowed": False, "provider": None, "model": None},
            "allowed_output_roots": []}


def bind_contract(job, contract):
    if job.get("kind") == "MigrationJob":
        job.update(track=contract["track"], adapter_version=contract["adapter"], supported_behaviours=[contract["scope"]], input_split={"seed": contract["seed"], **{kind: sum(case["kind"] == kind for case in contract["cases"]) for kind in KINDS}})


def count(value, maximum=9007199254740991):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ContractError("Invalid migration integer/count")


def validate_job(value, job_id, profile=None):
    dumps(value)
    if type(value) is not dict or value.get("job_id") != job_id:
        raise ContractError("Stored job identity contradicts the requested row")
    if value.get("kind") == "AssessmentJob":
        if set(value) & MIGRATION_FIELDS:
            raise ContractError("Current migration metadata cannot be downgraded to a legacy job")
        # Legacy schemas deliberately include sparse historical assessment rows.
        # They cannot manufacture a new MigrationJob merely by being read.
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ContractError("Unsupported legacy job version")
        return value
    if value.get("kind") != "MigrationJob" or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported migration job kind/version")
    required = BASE_FIELDS | MIGRATION_FIELDS
    if not required <= set(value) or not set(value) <= required | OPTIONAL_FIELDS:
        raise ContractError("Unknown or missing MigrationJob fields")
    identifier(job_id)
    identifier(value["profile"])
    if profile is not None and value["profile"] != profile:
        raise ContractError("Migration job is outside the current profile scope")
    count(value["revision"])
    if type(value["state"]) is not str or value["state"] not in STATES:
        raise ContractError("Unknown migration state")
    if type(value["repo"]) is not str or not Path(value["repo"]).is_absolute():
        raise ContractError("Absolute assessed repository required")
    if type(value["goal"]) is not str or not 1 <= len(value["goal"]) <= 4000:
        raise ContractError("Invalid migration goal")
    if type(value["assessment"]) is not dict:
        raise ContractError("Assessment identity required")
    digest(value["assessment"].get("source_digest"))
    if value["plan"] is not None and type(value["plan"]) is not dict:
        raise ContractError("Invalid stored plan")
    if type(value["execution_receipts"]) is not list or len(value["execution_receipts"]) > 1000 or type(value["execution_available"]) is not bool:
        raise ContractError("Invalid job evidence/availability metadata")
    if value["track"] is not None and value["track"] not in ("uplift", "transform", "reimagine"):
        raise ContractError("Unsupported migration track")
    if value["adapter_version"] not in (None, "json-batch-v1"):
        raise ContractError("Unsupported migration adapter")
    supported = value["supported_behaviours"]
    if type(supported) is not list or len(supported) > 100 or any(type(item) is not str or not 1 <= len(item) <= 4000 for item in supported):
        raise ContractError("Invalid declared behaviour scope")
    split = value["input_split"]
    fields(split, {"seed", *KINDS}, "input split")
    if split["seed"] is not None:
        count(split["seed"], 2147483647)
    for kind in KINDS:
        count(split[kind], 500)
    reference = value.get("behaviour_contract")
    if reference is None:
        if value["track"] is not None or value["adapter_version"] is not None or supported or split["seed"] is not None or any(split[kind] for kind in KINDS):
            raise ContractError("Migration metadata asserts a contract that is not registered")
    else:
        fields(reference, {"schema_version", "kind", "digest", "source_digest", "scope", "track", "adapter", "case_count", "fresh_count", "rule_count", "review_state", "adequacy"}, "behaviour contract reference")
        if type(reference["schema_version"]) is not int or reference["schema_version"] != 1 or reference["kind"] != "BehaviourContractReference":
            raise ContractError("Invalid behaviour contract reference version")
        digest(reference["digest"])
        for key in ("case_count", "fresh_count", "rule_count"):
            count(reference[key], 500)
        if value["track"] != reference["track"] or value["adapter_version"] != reference["adapter"] or supported != [reference["scope"]] or reference["source_digest"] != value["assessment"]["source_digest"] or split["fresh"] != reference["fresh_count"] or sum(split[kind] for kind in KINDS) != reference["case_count"]:
            raise ContractError("Migration metadata contradicts its protected contract scope/counts")
    budget = value["budget"]
    fields(budget, BUDGET_FIELDS, "migration budget")
    for key in BUDGET_FIELDS - {"model_tokens_used", "actual_cost"}:
        count(budget[key])
    if budget["model_tokens_used"] is not None:
        count(budget["model_tokens_used"])
    if budget["actual_cost"] is not None:
        raise ContractError("Actual provider cost is unmeasured; no cost assertion accepted")
    policy = value["model_policy"]
    fields(policy, {"enabled", "egress_allowed", "provider", "model"}, "model policy")
    if policy != {"enabled": False, "egress_allowed": False, "provider": None, "model": None} or any(type(policy[key]) is not bool for key in ("enabled", "egress_allowed")):
        raise ContractError("Model egress/orchestration is not enabled by job data")
    if budget["model_calls_used"] != 0:
        raise ContractError("No model calls are implemented or authorised for this job")
    roots = value["allowed_output_roots"]
    if type(roots) is not list or len(roots) > 100 or any(type(root) is not str or not Path(root).is_absolute() for root in roots):
        raise ContractError("Invalid owned output roots")
    if "fence_epoch" in value:
        count(value["fence_epoch"])
    if "failure_reason" in value and (type(value["failure_reason"]) is not str or len(value["failure_reason"]) > 4000):
        raise ContractError("Invalid stored failure reason")
    for name in OPTIONAL_FIELDS - {"fence_epoch", "failure_reason"}:
        if name in value and type(value[name]) is not dict:
            raise ContractError("Invalid job reference: " + name)
    return value


def job_schema():
    """Portable header export; private references have separate validators."""
    integer = {"type": "integer", "minimum": 0, "maximum": 9007199254740991}
    identity = {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"}
    props = {
        "schema_version": {"type": "integer", "const": 1}, "kind": {"const": "MigrationJob"},
        "job_id": identity, "profile": identity, "revision": integer,
        "state": {"type": "string", "enum": sorted(STATES)},
        "plan": {"type": ["object", "null"]}, "repo": {"type": "string", "minLength": 1, "format": "absolute-path"},
        "goal": {"type": "string", "minLength": 1, "maxLength": 4000},
        "assessment": {"type": "object", "required": ["source_digest"], "properties": {"source_digest": {"type": "string", "pattern": "^[a-f0-9]{64}$"}}},
        "execution_receipts": {"type": "array", "maxItems": 1000, "items": {"type": "object"}},
        "execution_available": {"type": "boolean"}, "track": {"enum": [None, "uplift", "transform", "reimagine"]},
        "adapter_version": {"enum": [None, "json-batch-v1"]},
        "supported_behaviours": {"type": "array", "maxItems": 100, "items": {"type": "string", "minLength": 1, "maxLength": 4000}},
        "input_split": {"type": "object", "required": ["seed", *KINDS], "additionalProperties": False, "properties": {"seed": {"type": ["integer", "null"], "minimum": 0, "maximum": 2147483647}, **{kind: {"type": "integer", "minimum": 0, "maximum": 500} for kind in KINDS}}},
        "budget": {"type": "object", "required": sorted(BUDGET_FIELDS), "additionalProperties": False, "properties": {**{key: integer for key in BUDGET_FIELDS - {"actual_cost", "model_tokens_used", "model_calls_used"}}, "model_calls_used": {"type": "integer", "const": 0}, "model_tokens_used": {"type": ["integer", "null"], "minimum": 0}, "actual_cost": {"type": "null"}}},
        "model_policy": {"type": "object", "const": metadata("default")["model_policy"]},
        "allowed_output_roots": {"type": "array", "maxItems": 100, "items": {"type": "string", "format": "absolute-path"}},
        **{name: {"type": "object"} for name in OPTIONAL_FIELDS - {"fence_epoch", "failure_reason"}},
        "fence_epoch": integer, "failure_reason": {"type": "string", "maxLength": 4000},
    }
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:hermes-modernisation:migration-job:v1", "title": "MigrationJob v1 header", "$comment": "Core bounded JSON validation additionally rejects numeric/bool coercion. Execution/review/contract references are authenticated and revalidated separately; this header schema does not establish their provenance or complete M1 evidence models.", "type": "object", "required": sorted(BASE_FIELDS | MIGRATION_FIELDS), "additionalProperties": False, "properties": props}

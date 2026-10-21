"""Versioned evidence output contracts: receipts, comparisons and proof reports.

These are strict, data-only descriptions of what the engine already emits. They
never upgrade bytes into proof: every value keeps NOT_PROVEN, an observed
receipt stays bound to the exact operation that was authorised, and a rendered
report may not claim more than its comparison. Legacy shapes are named
explicitly where they are still readable.
"""

import hashlib
import re

from .contracts import bounded_text, digest, fields
from .jsonio import ContractError, dumps, identifier

RECEIPT = "execution-receipt-v1"
COMPARISON = "evidence-comparison-v1"
REPORT = "proof-report-v1"
NAMES = (RECEIPT, COMPARISON, REPORT)

RECEIPT_GRADE = "observed-process-only"
OBSERVED_GRADE = "independently-observed-json-process-response"
VERDICT = "NOT_PROVEN"
IMAGE = re.compile(r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}")
MAX_BYTES = 9007199254740991

RECEIPT_FIELDS = {
    "schema_version", "kind", "grade", "actor", "profile", "job_id",
    "attempt_id", "phase", "source_digest", "oracle_digest",
    "environment_digest", "image", "authority_nonce", "process_exit_code",
    "timed_out", "truncated", "output_bytes", "input_sha256", "input_bytes",
    "input_complete", "output_sha256", "duration_seconds",
    "container_removed", "source_unchanged", "verdict", "missing_evidence",
}
RECEIPT_BINDINGS = {
    "job_id", "attempt_id", "profile", "phase", "source_digest",
    "oracle_digest", "environment_digest", "image", "authority_nonce",
    "input_sha256", "input_bytes",
}

OBSERVATION_REF_FIELDS = {
    "schema_version", "kind", "attempt_id", "sha256", "phase",
    "oracle_digest", "source_digest", "passed", "failed", "grade",
}
OBSERVED_CORE = {
    "schema_version", "job_id", "scope", "contract_scope", "source_digest",
    "verdict", "evidence_grade", "execution_performed", "compared_cases",
    "approved_differences", "missing_evidence", "unobserved_effects",
}
OBSERVED_OPTIONAL = {
    "baseline_passed", "baseline_failed", "candidate_passed",
    "candidate_failed", "cases", "baseline_receipt", "candidate_receipt",
    "rule_trace",
}
COMPARISON_CASE_FIELDS = {
    "id", "input_digest", "baseline_matches_expected",
    "candidate_matches_expected", "same_output", "rule_ids",
}
LEGACY_CORE = {
    "schema_version", "job_id", "scope", "verdict", "source_digest",
    "execution_performed", "missing_evidence", "compared_cases",
    "approved_differences",
}
LEGACY_OPTIONAL = {"comparison"}
INNER_FIELDS = {
    "schema_version", "verdict", "proof", "grade", "expectation_digest",
    "before_accepted", "after_accepted", "cases", "warnings",
    "missing_evidence",
}

REPORT_FIELDS = {
    "schema_version", "kind", "job_id", "scope", "source_digest", "verdict",
    "provenance", "comparison_sha256", "compared_cases", "rule_coverage",
    "claims", "missing_evidence", "unobserved_effects",
    "execution_performed",
}
PROVENANCE_OBSERVED = "protected-observed-pair"
PROVENANCE_REPORTED = "reported-junit-evidence"


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ContractError("Invalid bounded " + label)
    return value


def _boolean(value, label):
    if type(value) is not bool:
        raise ContractError("Strict boolean required for " + label)
    return value


def _number(value, low, high, label):
    if type(value) not in (int, float) or type(value) is bool or not low <= value <= high:
        raise ContractError("Invalid bounded " + label)
    return value


def _strings(value, low, high, maximum, label="evidence"):
    if type(value) is not list or not low <= len(value) <= high:
        raise ContractError("Bounded " + label + " text list required")
    for item in value:
        bounded_text(item, maximum, "evidence text")
    return value


def validate_observation_ref(value, label="observation reference"):
    fields(value, OBSERVATION_REF_FIELDS, label)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "ObservationReference":
        raise ContractError("Unsupported observation reference")
    identifier(value["attempt_id"])
    digest(value["sha256"])
    digest(value["oracle_digest"])
    digest(value["source_digest"])
    if value["phase"] not in ("baseline", "candidate") or value["grade"] != OBSERVED_GRADE:
        raise ContractError("Observation reference contradicts the observed grade")
    _integer(value["passed"], 0, 500, "observation pass count")
    _integer(value["failed"], 0, 500, "observation failure count")
    return value


def validate_receipt(value, *, bindings=None, require_collected=True):
    """Revalidate one process receipt against the exact authorised operation.

    The receipt is never trusted to describe itself as collected: callers pass
    the separately stored operation/journal values as ``bindings`` and this
    function refuses any disagreement. A missing or renamed version marker is a
    contract failure, not a legacy shape: no released store contains protected
    observations, and accepting unmarked receipts would open a downgrade hole.
    """
    fields(value, RECEIPT_FIELDS, "execution receipt")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "ExecutionReceipt":
        raise ContractError("Unsupported execution receipt schema")
    if value["grade"] != RECEIPT_GRADE or value["verdict"] != VERDICT:
        raise ContractError("Execution receipt carries a self-certified grade or verdict")
    identifier(value["actor"])
    identifier(value["profile"])
    identifier(value["job_id"])
    identifier(value["attempt_id"])
    if value["phase"] not in ("baseline", "candidate"):
        raise ContractError("Execution receipt phase is unsupported")
    for key in ("source_digest", "oracle_digest", "environment_digest", "output_sha256"):
        digest(value[key])
    if type(value["image"]) is not str or not IMAGE.fullmatch(value["image"]):
        raise ContractError("Execution receipt image is not digest-pinned")
    bounded_text(value["authority_nonce"], 500, "authority nonce")
    _integer(value["process_exit_code"], 0, 255, "process exit code")
    for key in ("timed_out", "truncated", "container_removed", "source_unchanged"):
        _boolean(value[key], key)
    _integer(value["output_bytes"], 0, MAX_BYTES, "output byte count")
    _number(value["duration_seconds"], 0, 86400, "measured duration")
    if value["input_sha256"] is None:
        if value["input_bytes"] != 0 or value["input_complete"] is not None:
            raise ContractError("Receipt without protected input contradicts its input fields")
    else:
        digest(value["input_sha256"])
        _integer(value["input_bytes"], 0, MAX_BYTES, "input byte count")
        _boolean(value["input_complete"], "input completeness")
    _strings(value["missing_evidence"], 1, 20, 4000, "receipt missing evidence")
    if bindings is not None:
        if type(bindings) is not dict or not set(bindings) <= RECEIPT_BINDINGS:
            raise ContractError("Unknown receipt binding requested")
        for key, expected in bindings.items():
            if value[key] != expected:
                raise ContractError("Execution receipt contradicts its authorised operation")
    if require_collected:
        if value["process_exit_code"] != 0 or value["timed_out"] or value["truncated"]:
            raise ContractError("Execution receipt is not a completed process collection")
        if not value["container_removed"] or not value["source_unchanged"]:
            raise ContractError("Execution receipt lacks verified cleanup or source identity")
        if value["input_complete"] is not True:
            raise ContractError("Execution receipt does not prove complete protected input")
    return value


def _comparison_common(value):
    identifier(value["job_id"])
    bounded_text(value["scope"], 4000, "comparison scope")
    digest(value["source_digest"])
    if value["verdict"] != VERDICT:
        raise ContractError("A comparison report cannot claim a stronger verdict")
    if value["execution_performed"] is not False:
        raise ContractError("A comparison report never performs execution")
    _integer(value["compared_cases"], 0, 500, "compared case count")
    from .differences import validate_approved
    validate_approved(value["approved_differences"])
    _strings(value["missing_evidence"], 0, 50, 4000)


def _comparison_case(value):
    fields(value, COMPARISON_CASE_FIELDS, "comparison case")
    identifier(value["id"])
    digest(value["input_digest"])
    for key in ("baseline_matches_expected", "candidate_matches_expected", "same_output"):
        _boolean(value[key], key)
    if type(value["rule_ids"]) is not list or any(type(item) is not str for item in value["rule_ids"]):
        raise ContractError("Invalid comparison rule links")
    for item in value["rule_ids"]:
        identifier(item)


def _inner_comparison(value):
    fields(value, INNER_FIELDS, "reported comparison")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported reported comparison version")
    if value["verdict"] not in ("SAME_SELECTED_SCOPE", "DIFFERS", "REFUSED_UNACCEPTED_EVIDENCE") or value["proof"] != VERDICT:
        raise ContractError("Reported comparison contradicts the evidence grade")
    bounded_text(value["grade"], 200, "reported comparison grade")
    digest(value["expectation_digest"])
    for key in ("before_accepted", "after_accepted"):
        _boolean(value[key], key)
    if type(value["cases"]) is not list or len(value["cases"]) > 500:
        raise ContractError("Bounded reported comparison cases required")
    for row in value["cases"]:
        fields(row, {"case", "before", "after", "verdict"}, "reported comparison case")
        if type(row["case"]) is not list or not all(type(item) is str for item in row["case"]):
            raise ContractError("Invalid reported comparison case identity")
        if row["verdict"] not in ("missing", "same", "differs"):
            raise ContractError("Invalid reported comparison case verdict")
        for key in ("before", "after"):
            if row[key] is not None and type(row[key]) is not str:
                raise ContractError("Invalid reported comparison outcome")
    fields(value["warnings"], {"before", "after", "delta"}, "reported warning counts")
    for key in ("before", "after", "delta"):
        _integer(value["warnings"][key], -500, 500, "reported warning count")
    _strings(value["missing_evidence"], 1, 20, 4000, "reported comparison missing evidence")


def validate_comparison(value):
    """Validate either public comparison lane without upgrading its grade."""
    if type(value) is not dict:
        raise ContractError("Unknown comparison shape")
    keys = set(value)
    if "evidence_grade" in keys or "contract_scope" in keys:
        if not OBSERVED_CORE <= keys or not keys <= OBSERVED_CORE | OBSERVED_OPTIONAL:
            raise ContractError("Observed comparison has unknown or missing fields")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["evidence_grade"] != OBSERVED_GRADE:
            raise ContractError("Observed comparison grade is unsupported")
        identifier(value["contract_scope"])
        _strings(value["unobserved_effects"], 1, 20, 4000)
        _comparison_common(value)
        present = keys & {"baseline_passed", "baseline_failed", "candidate_passed", "candidate_failed", "cases", "baseline_receipt", "candidate_receipt"}
        if present and present != {"baseline_passed", "baseline_failed", "candidate_passed", "candidate_failed", "cases", "baseline_receipt", "candidate_receipt"}:
            raise ContractError("Observed comparison carries partial observation details")
        if present:
            for key in ("baseline_passed", "baseline_failed", "candidate_passed", "candidate_failed"):
                _integer(value[key], 0, 500, "observed case count")
            if type(value["cases"]) is not list or len(value["cases"]) != value["compared_cases"]:
                raise ContractError("Observed comparison case rows do not match its count")
            for row in value["cases"]:
                _comparison_case(row)
            approved_ids = {entry["case_id"] for entry in value["approved_differences"]}
            if not approved_ids <= {row["id"] for row in value["cases"]}:
                raise ContractError("Approved difference names an absent comparison case")
            validate_observation_ref(value["baseline_receipt"], "baseline observation reference")
            validate_observation_ref(value["candidate_receipt"], "candidate observation reference")
            if value["baseline_receipt"]["phase"] != "baseline" or value["candidate_receipt"]["phase"] != "candidate":
                raise ContractError("Observation references are bound to the wrong phase")
        if "rule_trace" in keys:
            from .rule_trace import validate_trace

            trace = validate_trace(value["rule_trace"])
            if (
                trace["job_id"] != value["job_id"]
                or trace["source_digest"] != value["source_digest"]
            ):
                raise ContractError("Rule trace is bound to a different comparison")
        return value
    if not LEGACY_CORE <= keys or not keys <= LEGACY_CORE | LEGACY_OPTIONAL:
        raise ContractError("Comparison has unknown or missing fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("Unsupported comparison version")
    _comparison_common(value)
    if value["approved_differences"]:
        raise ContractError(
            "Recorded evidence has no sealed contract to approve a normalisation"
        )
    if "comparison" in value:
        _inner_comparison(value["comparison"])
        if value["compared_cases"] != len(value["comparison"]["cases"]):
            raise ContractError("Reported comparison count contradicts its case rows")
    return value


def proof_report(job, comparison):
    """Derive the only report shape the engine may publish for a comparison."""
    validate_comparison(comparison)
    provenance = PROVENANCE_OBSERVED if "evidence_grade" in comparison else PROVENANCE_REPORTED
    value = {
        "schema_version": 1,
        "kind": "ProofReport",
        "job_id": job["job_id"],
        "scope": job["goal"],
        "source_digest": job["assessment"]["source_digest"],
        "verdict": VERDICT,
        "provenance": provenance,
        "comparison_sha256": hashlib.sha256(dumps(comparison)).hexdigest(),
        "compared_cases": comparison["compared_cases"],
        "rule_coverage": comparison.get("rule_trace", {}).get(
            "coverage", "unverified"
        ),
        "claims": [],
        "missing_evidence": comparison["missing_evidence"],
        "unobserved_effects": comparison.get(
            "unobserved_effects",
            ["filesystem", "database", "network", "unexposed internal state"],
        ),
        "execution_performed": False,
    }
    return validate_proof_report(value)


def validate_proof_report(value):
    fields(value, REPORT_FIELDS, "proof report")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["kind"] != "ProofReport":
        raise ContractError("Unsupported proof report")
    identifier(value["job_id"])
    bounded_text(value["scope"], 4000, "proof report scope")
    digest(value["source_digest"])
    digest(value["comparison_sha256"])
    if value["verdict"] != VERDICT or value["claims"] != []:
        raise ContractError("A proof report cannot claim more than NOT_PROVEN")
    if value["provenance"] not in (PROVENANCE_OBSERVED, PROVENANCE_REPORTED):
        raise ContractError("Unknown proof report provenance")
    if value["rule_coverage"] not in {"unverified", "verified"}:
        raise ContractError("Unknown rule coverage state")
    if value["rule_coverage"] == "verified" and value["provenance"] != PROVENANCE_OBSERVED:
        raise ContractError("Only protected observed evidence can verify rule coverage")
    _integer(value["compared_cases"], 0, 500, "proof report case count")
    _strings(value["missing_evidence"], 0, 50, 4000)
    _strings(value["unobserved_effects"], 1, 20, 4000)
    if value["execution_performed"] is not False:
        raise ContractError("A proof report is rendered data, never execution")
    return value


def _schema(identifier_value, title, comment, required, properties):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:hermes-modernisation:" + identifier_value,
        "title": title,
        "$comment": comment,
        "type": "object",
        "additionalProperties": False,
        "required": sorted(required),
        "properties": properties,
    }


def _sha():
    return {"type": "string", "pattern": "^[a-f0-9]{64}$"}


def receipt_schema():
    text = {"type": "string", "minLength": 1, "maxLength": 4000}
    return _schema(
        "execution-receipt:v1",
        "ExecutionReceipt v1 observed process collection",
        "Data-only receipt shape. Core validation binds it to the separately stored operation and refuses any self-certified grade, verdict, exit status, cleanup or input completeness. A receipt is not permission and not proof.",
        RECEIPT_FIELDS,
        {
            "schema_version": {"type": "integer", "const": 1},
            "kind": {"const": "ExecutionReceipt"},
            "grade": {"const": RECEIPT_GRADE},
            "verdict": {"const": VERDICT},
            "actor": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "profile": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "job_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "attempt_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "phase": {"enum": ["baseline", "candidate"]},
            "source_digest": _sha(),
            "oracle_digest": _sha(),
            "environment_digest": _sha(),
            "output_sha256": _sha(),
            "image": {"type": "string", "pattern": "^[a-z0-9./_-]+@sha256:[a-f0-9]{64}$"},
            "authority_nonce": {"type": "string", "minLength": 1, "maxLength": 500},
            "process_exit_code": {"type": "integer", "minimum": 0, "maximum": 255},
            "timed_out": {"type": "boolean"},
            "truncated": {"type": "boolean"},
            "container_removed": {"type": "boolean"},
            "source_unchanged": {"type": "boolean"},
            "output_bytes": {"type": "integer", "minimum": 0, "maximum": MAX_BYTES},
            "input_bytes": {"type": "integer", "minimum": 0, "maximum": MAX_BYTES},
            "input_sha256": {"type": ["string", "null"], "pattern": "^[a-f0-9]{64}$"},
            "input_complete": {"type": ["boolean", "null"]},
            "duration_seconds": {"type": "number", "minimum": 0, "maximum": 86400},
            "missing_evidence": {"type": "array", "minItems": 1, "maxItems": 20, "uniqueItems": True, "items": text},
        },
    )


def comparison_schema():
    text = {"type": "string", "minLength": 1, "maxLength": 4000}
    ref = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(OBSERVATION_REF_FIELDS),
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "kind": {"const": "ObservationReference"},
            "attempt_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "sha256": _sha(),
            "phase": {"enum": ["baseline", "candidate"]},
            "oracle_digest": _sha(),
            "source_digest": _sha(),
            "passed": {"type": "integer", "minimum": 0, "maximum": 500},
            "failed": {"type": "integer", "minimum": 0, "maximum": 500},
            "grade": {"const": OBSERVED_GRADE},
        },
    }
    case = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(COMPARISON_CASE_FIELDS),
        "properties": {
            "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "input_digest": _sha(),
            "baseline_matches_expected": {"type": "boolean"},
            "candidate_matches_expected": {"type": "boolean"},
            "same_output": {"type": "boolean"},
            "rule_ids": {"type": "array", "items": {"type": "string"}},
        },
    }
    return _schema(
        "evidence-comparison:v1",
        "EvidenceComparison v1 public comparison",
        "Two named lanes: the observed lane binds protected observation references and the reported lane binds candidate-authored per-case evidence. Neither lane may claim PROVEN, perform execution, or carry approved differences without a separate reviewed contract.",
        LEGACY_CORE,
        {
            "schema_version": {"type": "integer", "const": 1},
            "job_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "scope": {"type": "string", "minLength": 1, "maxLength": 4000},
            "source_digest": _sha(),
            "verdict": {"const": VERDICT},
            "execution_performed": {"const": False},
            "compared_cases": {"type": "integer", "minimum": 0, "maximum": 500},
            "approved_differences": {"type": "array", "const": []},
            "missing_evidence": {"type": "array", "maxItems": 50, "items": text},
            "contract_scope": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "evidence_grade": {"const": OBSERVED_GRADE},
            "unobserved_effects": {"type": "array", "minItems": 1, "maxItems": 20, "items": text},
            "baseline_passed": {"type": "integer", "minimum": 0, "maximum": 500},
            "baseline_failed": {"type": "integer", "minimum": 0, "maximum": 500},
            "candidate_passed": {"type": "integer", "minimum": 0, "maximum": 500},
            "candidate_failed": {"type": "integer", "minimum": 0, "maximum": 500},
            "cases": {"type": "array", "maxItems": 500, "items": case},
            "baseline_receipt": ref,
            "candidate_receipt": ref,
            "comparison": {"type": "object"},
        },
    )


def report_schema():
    text = {"type": "string", "minLength": 1, "maxLength": 4000}
    return _schema(
        "proof-report:v1",
        "ProofReport v1 bounded verdict",
        "Everything a rendered report may claim about evidence. Rule coverage stays unverified until a separate reviewed rule/adequacy contract exists; claims stay empty and the verdict stays NOT_PROVEN.",
        REPORT_FIELDS,
        {
            "schema_version": {"type": "integer", "const": 1},
            "kind": {"const": "ProofReport"},
            "job_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,100}$"},
            "scope": {"type": "string", "minLength": 1, "maxLength": 4000},
            "source_digest": _sha(),
            "verdict": {"const": VERDICT},
            "provenance": {"enum": [PROVENANCE_OBSERVED, PROVENANCE_REPORTED]},
            "comparison_sha256": _sha(),
            "compared_cases": {"type": "integer", "minimum": 0, "maximum": 500},
            "rule_coverage": {"const": "unverified"},
            "claims": {"type": "array", "const": []},
            "missing_evidence": {"type": "array", "maxItems": 50, "items": text},
            "unobserved_effects": {"type": "array", "minItems": 1, "maxItems": 20, "items": text},
            "execution_performed": {"const": False},
        },
    )


def descriptor(name):
    builders = {RECEIPT: receipt_schema, COMPARISON: comparison_schema, REPORT: report_schema}
    if name not in builders:
        raise ContractError("Unsupported schema name/version")
    schema = builders[name]()
    return {
        "schema_version": 1, "kind": "SchemaDescriptor", "name": name,
        "schema": schema, "sha256": hashlib.sha256(dumps(schema)).hexdigest(),
        "permission_granted": False, "execution_performed": False,
    }

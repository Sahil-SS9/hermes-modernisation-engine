"""Source-read-only assessment/planning service. Never grants execution."""

from pathlib import Path
from . import evidence
from . import recipes
from .identity import snapshot
from .inventory import assess
from .jsonio import ContractError, dumps
from .store import Store
from .report import render

FIELDS = {
    "assess": {"repo", "goal", "request_id"},
    "inventory": {"job", "section", "page"},
    "plan": {"job", "revision"},
    "status": {"job"},
    "record": {"job", "phase", "expectation", "output", "source_digest"},
    "protocol": set(),
    "response_protocol": set(),
    "schema": {"name"},
    "contract": {"job", "revision", "contract"},
    "prepare": {"job", "phase", "actor", "request_id", "timeout_seconds", "output_limit_bytes"},
    "attempts": {"job"},
    "review_request": {"job", "purpose", "actor"},
    "review": {"job", "grant"},
    "run": {"job", "attempt", "grant"},
    "resume": {"job", "attempt"},
    "proposal": {"job", "revision", "proposal"},
    "build": {"job"},
    "control_request": {"job", "attempt", "purpose", "actor"},
    "cancel": {"job", "attempt", "grant"},
    "recover": {"job", "attempt", "grant"},
    "recover_build": {"job", "attempt", "grant"},
    "recipe": {"repo", "recipe", "base_digest", "dest"},
    "compare": {"job"},
    "report": {"job"},
}


class Engine:
    def __init__(self, root, *, profile="default", operator_config=None):
        from .jsonio import identifier
        self.profile = identifier(profile)
        self.store = Store(root, profile=self.profile)
        self.operator_config = operator_config

    def invoke(self, action, arguments):
        if action == "approve" or (action in ("run", "resume") and self.operator_config is None):
            raise ContractError(
                "EXECUTION_UNAVAILABLE: trusted operator configuration and exact signed authority required; text is not authority"
            )
        if (
            action not in FIELDS
            or type(arguments) is not dict
            or not set(arguments) <= FIELDS[action]
        ):
            raise ContractError("Unknown operation or argument")
        if action == "status" and not arguments:
            return {
                "schema_version": 1,
                "implementation_status": "READ_ONLY_PREVIEW",
                "execution_available": False,
                "missing_evidence": [
                    "complete execution and behavioural proof lanes",
                    "release acceptance",
                ],
                "implemented": [
                    "assess",
                    "plan",
                    "status",
                    "record",
                    "recipe",
                    "compare-gaps",
                    "report-gaps",
                    "protocol-descriptor",
                    "unreviewed-protected-contract",
                    "unsigned-operation-preparation",
                    "attempt-journal",
                ],
            }
        required = FIELDS[action]
        if set(arguments) != required:
            raise ContractError("Required arguments missing")
        if action == "schema":
            import hashlib
            from .models import job_schema
            if arguments["name"] == "migration-job-v1":
                schema = job_schema()
            elif arguments["name"] == "business-rule-v1":
                from .rules import rule_schema
                schema = rule_schema()
            else:
                from .evidence_contracts import NAMES, descriptor
                if arguments["name"] in NAMES:
                    return descriptor(arguments["name"])
                raise ContractError("Unsupported schema name/version")
            return {"schema_version": 1, "kind": "SchemaDescriptor", "name": arguments["name"], "schema": schema, "sha256": hashlib.sha256(dumps(schema)).hexdigest(), "permission_granted": False, "execution_performed": False}
        if action == "assess":
            repo = Path(arguments["repo"])
            data_root = self.store.root.resolve()
            resolved = repo.resolve()
            if data_root.is_relative_to(resolved) or resolved.is_relative_to(data_root):
                raise ContractError("Source and private job storage must not overlap")
            report = assess(repo)
            return self.store.create(
                arguments["request_id"], str(repo), arguments["goal"], report, migration=True
            )
        if action == "inventory":
            return self.store.details(
                arguments["job"], arguments["section"], arguments["page"]
            )
        if action == "protocol":
            return evidence.protocol()
        if action == "response_protocol":
            from .baseline import protocol
            return protocol()
        if action == "recipe":
            return recipes.apply(
                arguments["recipe"],
                arguments["repo"],
                arguments["base_digest"],
                arguments["dest"],
            )
        job = self.store.get(arguments["job"])
        if action == "contract":
            from .contracts import validate_contract

            contract = validate_contract(
                arguments["contract"], job["repo"], job["assessment"]["source_digest"]
            )
            return self.store.save_contract(job["job_id"], arguments["revision"], contract)
        if action == "control_request":
            from .control import request
            return request(self.store, job, arguments["attempt"], arguments["purpose"], arguments["actor"], self.profile)
        if action == "recover_build":
            from .operator import OperatorPolicy
            from .build_recovery import recover
            policy = OperatorPolicy(self.operator_config, self.profile, self.store.root, job["repo"])
            return recover(self.store, job, arguments["attempt"], arguments["grant"], policy)
        if action in {"cancel", "recover"}:
            from .operator import OperatorPolicy
            from . import control
            policy = OperatorPolicy(self.operator_config, self.profile, self.store.root, job["repo"])
            function = control.cancel if action == "cancel" else control.recover
            return function(self.store, job, arguments["attempt"], arguments["grant"], policy)
        if action == "proposal":
            from .candidates import save_proposal
            return save_proposal(self.store, job, arguments["revision"], arguments["proposal"])
        if action in {"run", "resume", "build"}:
            from .operator import OperatorPolicy
            policy = OperatorPolicy(self.operator_config, self.profile, self.store.root, job["repo"])
            if action == "build":
                from .candidates import build
                return build(self.store, job, policy)
            from . import controller
            if action == "run":
                return controller.run(self.store, job, arguments["attempt"], arguments["grant"], policy)
            return controller.resume(self.store, job, arguments["attempt"], policy)
        if action == "review_request":
            from .reviews import request
            return request(self.store, job, arguments["purpose"], arguments["actor"], self.profile)
        if action == "review":
            from .operator import OperatorPolicy
            from .reviews import accept
            policy = OperatorPolicy(self.operator_config, self.profile, self.store.root, job["repo"])
            return accept(self.store, job, arguments["grant"], policy)
        if action == "attempts":
            return {"schema_version": 1, "job_id": job["job_id"], "attempts": self.store.attempts_for(job["job_id"])}
        if action == "prepare":
            from .runtime import prepare_request
            return prepare_request(self.store, job, arguments, profile=self.profile)
        if action == "status":
            return job
        if action == "record":
            return evidence.record(self.store, arguments)
        if action == "plan":
            if (
                snapshot(Path(job["repo"]))["digest"]
                != job["assessment"]["source_digest"]
            ):
                raise ContractError(
                    "Source changed; create a fresh assessment, do not reuse baseline identity"
                )
            plan = {
                "schema_version": 1,
                "goal": job["goal"],
                "source_digest": job["assessment"]["source_digest"],
                "approved": False,
                "contract_review_required": True,
                "steps": [
                    "Review lexical inventory and unknown behaviours",
                    "Define and protect independent oracle inputs",
                    "Obtain separate authentic baseline execution grant",
                    "Capture baseline before approving migration",
                    "Review candidate patch, then separately grant candidate execution",
                    "Compare verified stored receipts",
                ],
                "allowed_candidate_paths": [],
                "planned_differences": [],
                "unknowns": job["assessment"]["missing_evidence"],
            }
            return self.store.save_plan(job["job_id"], arguments["revision"], plan)
        if job.get("baseline_ref") or job.get("candidate_observation_ref"):
            from .operator import OperatorPolicy
            from .observations import comparison as observed_comparison
            policy = OperatorPolicy(self.operator_config, self.profile, self.store.root, job["repo"])
            comparison = observed_comparison(self.store, job, policy)
        else:
            comparison = evidence.comparison(job, self.store.evidence_for(job["job_id"]))
        from .evidence_contracts import proof_report, validate_comparison
        comparison = validate_comparison(comparison)
        if action == "compare":
            return comparison
        proof = proof_report(job, comparison)
        return {
            "json": dumps(proof).decode(),
            "html": render(job, comparison),
            "text": "NOT_PROVEN within requested scope: "
            + job["goal"]
            + "\n"
            + "\n".join("- " + gap for gap in proof["missing_evidence"]),
            "proof_report": proof,
        }

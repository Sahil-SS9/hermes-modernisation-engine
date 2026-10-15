"""Source-read-only assessment/planning service. Never grants execution."""

from pathlib import Path
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
    "compare": {"job"},
    "report": {"job"},
}


class Engine:
    def __init__(self, root):
        self.store = Store(root)

    def invoke(self, action, arguments):
        if action in ("run", "resume", "approve"):
            raise ContractError(
                "EXECUTION_UNAVAILABLE: complete trusted executor acceptance required; text is not authority"
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
                    "compare-gaps",
                    "report-gaps",
                ],
            }
        required = FIELDS[action]
        if set(arguments) != required:
            raise ContractError("Required arguments missing")
        if action == "assess":
            repo = Path(arguments["repo"])
            data_root = self.store.root.resolve()
            resolved = repo.resolve()
            if data_root.is_relative_to(resolved) or resolved.is_relative_to(data_root):
                raise ContractError("Source and private job storage must not overlap")
            report = assess(repo)
            return self.store.create(
                arguments["request_id"], str(repo), arguments["goal"], report
            )
        if action == "inventory":
            return self.store.details(
                arguments["job"], arguments["section"], arguments["page"]
            )
        job = self.store.get(arguments["job"])
        if action == "status":
            return job
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
        gaps = list(job["assessment"]["missing_evidence"])
        gaps.append(
            "No accepted executor receipt pair is stored for this assessment job"
        )
        comparison = {
            "schema_version": 1,
            "job_id": job["job_id"],
            "scope": job["goal"],
            "verdict": "NOT_PROVEN",
            "source_digest": job["assessment"]["source_digest"],
            "execution_performed": False,
            "missing_evidence": gaps,
            "compared_cases": 0,
            "approved_differences": [],
        }
        if action == "compare":
            return comparison
        return {
            "json": dumps(comparison).decode(),
            "html": render(job, comparison),
            "text": "NOT_PROVEN within requested scope: "
            + job["goal"]
            + "\n"
            + "\n".join("- " + gap for gap in gaps),
        }

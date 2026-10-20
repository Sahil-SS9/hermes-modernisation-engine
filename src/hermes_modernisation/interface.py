"""Host-neutral shared CLI and tool argument contracts; no host imports."""

from .jsonio import ContractError, loads

OPERATIONS = (
    "assess",
    "inventory",
    "plan",
    "status",
    "record",
    "protocol",
    "response_protocol",
    "schema",
    "contract",
    "prepare",
    "attempts",
    "review_request",
    "review",
    "proposal",
    "build",
    "control_request",
    "cancel",
    "recover",
    "recover_build",
    "recipe",
    "compare",
    "report",
    "run",
    "resume",
)
PROPERTIES = {
    "section": {
        "type": "string",
        "enum": ["symbols", "dependencies", "rules", "files"],
    },
    "page": {"type": "integer", "minimum": 0},
    "actor": {"type": "string"},
    "name": {"type": "string", "enum": ["migration-job-v1"]},
    "attempt": {"type": "string"},
    "purpose": {"type": "string", "enum": ["contract", "migration", "cancel", "recover", "recover_build"]},
    "grant": {"type": "object", "additionalProperties": True},
    "proposal": {"type": "object", "additionalProperties": True},
    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 600},
    "output_limit_bytes": {"type": "integer", "minimum": 1, "maximum": 4194304},
    "repo": {"type": "string"},
    "goal": {"type": "string"},
    "request_id": {"type": "string"},
    "job": {"type": "string"},
    "revision": {"type": "integer", "minimum": 0},
    "phase": {"type": "string", "enum": ["baseline", "candidate"]},
    "expectation": {"type": "object", "additionalProperties": True},
    "contract": {"type": "object", "additionalProperties": True},
    "output": {"type": "string"},
    "source_digest": {"type": "string"},
    "recipe": {"type": "string"},
    "base_digest": {"type": "string"},
    "dest": {"type": "string"},
}
REQUIRED = {
    "assess": ["repo", "goal", "request_id"],
    "inventory": ["job", "section", "page"],
    "plan": ["job", "revision"],
    "status": [],
    "record": ["job", "phase", "expectation", "output", "source_digest"],
    "protocol": [],
    "response_protocol": [],
    "schema": ["name"],
    "contract": ["job", "revision", "contract"],
    "prepare": ["job", "phase", "actor", "request_id", "timeout_seconds", "output_limit_bytes"],
    "attempts": ["job"],
    "review_request": ["job", "purpose", "actor"],
    "review": ["job", "grant"],
    "proposal": ["job", "revision", "proposal"],
    "build": ["job"],
    "control_request": ["job", "attempt", "purpose", "actor"],
    "cancel": ["job", "attempt", "grant"],
    "recover": ["job", "attempt", "grant"],
    "recover_build": ["job", "attempt", "grant"],
    "run": ["job", "attempt", "grant"],
    "resume": ["job", "attempt"],
    "recipe": ["repo", "recipe", "base_digest", "dest"],
    "compare": ["job"],
    "report": ["job"],
}


def setup(parser):
    parser.add_argument("operation", choices=OPERATIONS, nargs="?", default="status")
    parser.add_argument("--repo")
    parser.add_argument("--goal")
    parser.add_argument("--request-id")
    parser.add_argument("--job")
    parser.add_argument(
        "--section", choices=["symbols", "dependencies", "rules", "files"]
    )
    parser.add_argument("--page", type=int)
    parser.add_argument("--revision", type=int)
    parser.add_argument("--actor")
    parser.add_argument("--name", choices=["migration-job-v1"])
    parser.add_argument("--attempt")
    parser.add_argument("--purpose", choices=["contract", "migration", "cancel", "recover", "recover_build"])
    parser.add_argument("--grant")
    parser.add_argument("--proposal")
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--output-limit-bytes", type=int)
    parser.add_argument("--phase", choices=["baseline", "candidate"])
    parser.add_argument("--expectation")
    parser.add_argument("--contract")
    parser.add_argument("--output")
    parser.add_argument("--source-digest")
    parser.add_argument("--recipe")
    parser.add_argument("--base-digest")
    parser.add_argument("--dest")


def arguments_for(fields):
    for key in ("expectation", "contract", "grant", "proposal"):
        if isinstance(fields.get(key), str):
            try:
                fields[key] = loads(fields[key])
            except ContractError as error:
                raise ContractError(key.title() + " must be a bounded duplicate-free JSON object") from error
    return {key: value for key, value in fields.items() if value is not None}



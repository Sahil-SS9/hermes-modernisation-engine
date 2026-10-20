"""Thin public SDK adapter; all surfaces call the same host-neutral service."""

import argparse
import json
import shlex
from ..service import Engine
from ..jsonio import ContractError, loads

OPERATIONS = (
    "assess",
    "inventory",
    "plan",
    "status",
    "record",
    "protocol",
    "contract",
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
    "contract": ["job", "revision", "contract"],
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
    parser.add_argument("--phase", choices=["baseline", "candidate"])
    parser.add_argument("--expectation")
    parser.add_argument("--contract")
    parser.add_argument("--output")
    parser.add_argument("--source-digest")
    parser.add_argument("--recipe")
    parser.add_argument("--base-digest")
    parser.add_argument("--dest")


def arguments_for(fields):
    for key in ("expectation", "contract"):
        if isinstance(fields.get(key), str):
            try:
                fields[key] = loads(fields[key])
            except ContractError as error:
                raise ContractError(key.title() + " must be a bounded duplicate-free JSON object") from error
    return {key: value for key, value in fields.items() if value is not None}


DESCRIPTIONS = {
    "contract": (
        "Register an unreviewed protected JSON-response contract and exact source citations. "
        "Expected values stay in private job storage, outside candidate mounts. "
        "This stores data only, grants no authority and runs no app or model."
    ),
    "record": (
        "Record operator-evaluated retained run output for a job after trusted "
        "per-case evaluation. Never runs repository code or models. Recorded "
        "data is candidate-authored JUnit evidence, never authenticated proof."
    ),
    "protocol": (
        "Read-only descriptor of the owned junit-stdout-v1 producer program "
        "(bytes plus SHA-256). Runs nothing by itself."
    ),
    "recipe": (
        "Apply the fixed reviewed metadata recipe (NO AI, no dependency "
        "resolution, no installation) to produce a disposable candidate root. "
        "Text metadata files get a per-file unified diff; the uv.lock lane "
        "replays owner-reviewed, hash-pinned candidate bytes, with provenance "
        "plus a package-level delta as the declared lock review surface "
        "instead of a line-level diff. Original source is never modified."
    ),
}


def register(ctx):
    def invoke(action, arguments):
        try:
            # Resolve profile scope on EVERY call, never at module import.
            from plugins.plugin_storage import plugin_data_dir

            return Engine(plugin_data_dir("modernisation-engine") / "private").invoke(
                action, arguments
            )
        except (ContractError, OSError, ValueError) as error:
            return {
                "error": "EXECUTION_UNAVAILABLE"
                if action in ("run", "resume", "approve")
                else "INVALID_REQUEST",
                "message": str(error),
                "execution_performed": False,
            }

    def cli(arguments):
        fields = {key: getattr(arguments, key, None) for key in PROPERTIES}
        try:
            result = invoke(arguments.operation, arguments_for(fields))
        except ContractError as error:
            result = {"error": "INVALID_ARGUMENTS", "message": str(error), "execution_performed": False}
        print(json.dumps(result))
        if "error" in result:
            raise SystemExit(2)

    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise ContractError(message)

    def slash(raw_args):
        try:
            words = shlex.split(raw_args or "status")
            if words and words[0] in ("run", "resume", "approve"):
                return json.dumps(invoke(words[0], {}))
            parser = Parser(add_help=False)
            setup(parser)
            arguments = parser.parse_args(words)
            fields = {key: getattr(arguments, key, None) for key in PROPERTIES}
            return json.dumps(
                invoke(arguments.operation, arguments_for(fields))
            )
        except (ContractError, ValueError) as error:
            return json.dumps({"error": "INVALID_ARGUMENTS", "message": str(error)})

    handles = []
    try:
        for register_one in (
            lambda: ctx.register_cli_command(
                "modernise",
                "Migration source assessment and evidence status",
                setup,
                cli,
            ),
            lambda: ctx.register_command(
                "modernise",
                slash,
                description="Assess sources, plan review and inspect evidence; execution gated",
                args_hint="<operation> [options]",
                argument_mode="text",
            ),
        ):
            handle = register_one()
            if handle is None:
                raise RuntimeError(
                    "Modernisation namespace collision; registration refused"
                )
            handles.append(handle)
        for action, required in REQUIRED.items():
            fields = required if action != "status" else ["job"]
            parameters = {
                "type": "object",
                "properties": {key: PROPERTIES[key] for key in fields},
                "required": required,
                "additionalProperties": False,
            }

            def handler(arguments, _action=action, **kwargs):
                return json.dumps(invoke(_action, arguments))

            handle = ctx.register_tool(
                "modernise_" + action,
                "modernisation-engine",
                {
                    "name": "modernise_" + action,
                    "description": DESCRIPTIONS.get(
                        action,
                        "Source-read-only "
                        + action
                        + ". Writes only plugin-owned job metadata. Never runs repository code or models.",
                    ),
                    "parameters": parameters,
                },
                handler,
            )
            if handle is None:
                raise RuntimeError("Modernisation tool collision; registration refused")
            handles.append(handle)
    except BaseException:
        for handle in reversed(handles):
            handle.dispose()
        raise

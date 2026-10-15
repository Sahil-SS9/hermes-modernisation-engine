"""Thin public SDK adapter; all surfaces call the same host-neutral service."""

import argparse
import json
import shlex
from ..service import Engine
from ..jsonio import ContractError

OPERATIONS = (
    "assess",
    "inventory",
    "plan",
    "status",
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
}
REQUIRED = {
    "assess": ["repo", "goal", "request_id"],
    "inventory": ["job", "section", "page"],
    "plan": ["job", "revision"],
    "status": [],
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
        result = invoke(
            arguments.operation,
            {key: value for key, value in fields.items() if value is not None},
        )
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
                invoke(
                    arguments.operation,
                    {key: value for key, value in fields.items() if value is not None},
                )
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
                    "description": "Source-read-only "
                    + action
                    + ". Writes only plugin-owned job metadata. Never runs repository code or models.",
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

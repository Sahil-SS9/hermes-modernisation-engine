"""Thin public SDK adapter; all surfaces call the same host-neutral service."""

import argparse
import json
import shlex
from ..service import Engine
from ..jsonio import ContractError

from ..interface import (
    OPERATIONS as OPERATIONS, PROPERTIES, REQUIRED, setup, arguments_for,
)

DESCRIPTIONS = {
    "schema": "Read the versioned MigrationJob header definition and SHA-256. No private job/expected values, filesystem writes, approvals, programs or model calls. Referenced execution/review evidence is validated separately.",
    "recover_build": "With a fresh exact signed owner decision and no active builder, quarantine the reserved candidate without deletion/reuse, retain failed files and require a new migration review and fresh candidate namespace. No program/model execution.",
    "control_request": "Prepare an unsigned exact owner cancel/recovery decision for a stored attempt. No Docker access, permission or program replay.",
    "cancel": "Persist a separately signed owner cooperative-stop request. Never steals the live worker runtime lock; uncertain/lost work needs explicit recovery.",
    "recover": "With a fresh exact signed owner control grant and no live runtime owner, retire only the stored attempt container, verify absence and fence old workers. Never replays code or adopts partial evidence; fresh execution needs a new attempt/grant.",
    "review_request": "Prepare an unsigned exact owner review decision for the current private contract/proposal. Does not approve or execute anything.",
    "review": "Accept only an authentic externally signed exact owner review against trusted enrolled public keys. Review does not permit process execution; caller text is never authority.",
    "proposal": "Register a bounded literal source proposal after a protected baseline. No execution or approval; paths and source preimages are checked.",
    "build": "Materialise the separately owner-reviewed proposal at an engine-reserved candidate path. No programs, installs or models run; source stays unchanged.",
    "run": "Execute one exact stored attempt only with current trusted configuration, signed one-use operation authority and protected review prerequisites. Network off, fixed rootless limits, no implicit retry or merge.",
    "resume": "Revalidate an already completed stored execution only. Pending, interrupted or uncertain execution requires explicit recovery; never blindly replays programs.",
    "response_protocol": "Describe input-only JSON process requests and actual JSON responses. No expected values, execution, model calls or proof are produced by this descriptor.",
    "prepare": "Persist an UNSIGNED exact execution request. No permission, process, model or automatic replay. An actor label is not approval.",
    "attempts": "Read private job attempt metadata, without worker capabilities, execution or writes.",
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

            getter = getattr(ctx, "get_config", None)
            operator_config = getter("operator_config", None) if callable(getter) else None
            return Engine(plugin_data_dir("modernisation-engine") / "private", operator_config=operator_config).invoke(
                action, arguments
            )
        except (ContractError, OSError, ValueError, PermissionError) as error:
            from ..errors import result as error_result
            return error_result(error, action)

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
            getter = getattr(ctx, "get_config", None)
            configured = getter("operator_config", None) if callable(getter) else None
            if words and (words[0] == "approve" or (words[0] in ("run", "resume") and configured is None)):
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
                # The host capability probe may skip optional CLI/slash surfaces
                # and return None. Treat that as an unavailable surface, not a
                # collision; the registered tools below remain fail-closed.
                continue
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
            if handle is not None:
                handles.append(handle)
    except BaseException:
        for handle in reversed(handles):
            handle.dispose()
        raise

"""Standalone CLI; explicit operator configuration, no credentials or fallback."""

import argparse
import json
from pathlib import Path

from .interface import PROPERTIES, arguments_for, setup
from .service import Engine
from .jsonio import ContractError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Modernisation Engine bounded private workflow")
    parser.add_argument("--data-dir", type=Path, required=True)
    # CLI composition inputs, deliberately absent from model/tool argument schemas.
    parser.add_argument("--operator-config", type=Path)
    parser.add_argument("--profile", default="default")
    setup(parser)
    args = parser.parse_args(argv)
    fields = {key: getattr(args, key, None) for key in PROPERTIES}
    try:
        arguments = arguments_for(fields)
    except ContractError as error:
        print(json.dumps({"error": "INVALID_ARGUMENTS", "message": str(error), "execution_performed": False}))
        return 2
    try:
        result = Engine(args.data_dir, profile=args.profile, operator_config=args.operator_config).invoke(args.operation, arguments)
    except (ContractError, OSError, ValueError, PermissionError) as error:
        print(json.dumps({"error": "EXECUTION_UNAVAILABLE" if args.operation in ("run", "resume") else "INVALID_REQUEST", "message": str(error), "execution_performed": False}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

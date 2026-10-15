"""Standalone source assessment CLI; host data root must be explicit."""

import argparse
import json
from pathlib import Path
from .service import Engine
from .jsonio import ContractError


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Modernisation Engine source-read-only preview"
    )
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument(
        "operation",
        choices=[
            "assess",
            "inventory",
            "plan",
            "status",
            "compare",
            "report",
            "run",
            "resume",
        ],
    )
    parser.add_argument("--repo")
    parser.add_argument("--goal")
    parser.add_argument("--request-id")
    parser.add_argument("--job")
    parser.add_argument(
        "--section", choices=["symbols", "dependencies", "rules", "files"]
    )
    parser.add_argument("--page", type=int)
    parser.add_argument("--revision", type=int)
    args = parser.parse_args(argv)
    fields = {
        key: value
        for key, value in vars(args).items()
        if key not in ("data_dir", "operation") and value is not None
    }
    try:
        result = Engine(args.data_dir).invoke(args.operation, fields)
    except (ContractError, OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "error": "EXECUTION_UNAVAILABLE"
                    if args.operation in ("run", "resume")
                    else "INVALID_REQUEST",
                    "message": str(error),
                }
            )
        )
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

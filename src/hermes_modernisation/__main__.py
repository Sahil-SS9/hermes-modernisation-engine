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
            "record",
            "protocol",
            "recipe",
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
    parser.add_argument("--phase", choices=["baseline", "candidate"])
    parser.add_argument("--expectation")
    parser.add_argument("--output")
    parser.add_argument("--source-digest")
    parser.add_argument("--recipe")
    parser.add_argument("--base-digest")
    parser.add_argument("--dest")
    args = parser.parse_args(argv)
    fields = {
        key: value
        for key, value in vars(args).items()
        if key not in ("data_dir", "operation") and value is not None
    }
    expectation = fields.get("expectation")
    if isinstance(expectation, str):
        try:
            fields["expectation"] = json.loads(expectation)
        except (ValueError, TypeError, RecursionError) as error:
            print(
                json.dumps({"error": "INVALID_ARGUMENTS", "message": str(error)})
            )
            return 2
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

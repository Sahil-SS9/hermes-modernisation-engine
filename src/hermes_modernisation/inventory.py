"""Conservative lexical assessment. AST facts are not business-rule proof."""

import ast
import hashlib
from pathlib import Path
from .identity import snapshot, read_source
from .jsonio import ContractError


LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".cs": "csharp",
}


def assess(repo):
    repo = Path(repo)
    manifest = snapshot(repo)
    symbols = []
    dependencies = []
    rules = []
    languages = {}
    errors = []
    unsupported = []
    for record in manifest["files"]:
        path = record["path"]
        language = LANGUAGES.get(Path(path).suffix)
        if not language:
            continue
        languages[language] = languages.get(language, 0) + 1
        if language != "python":
            unsupported.append(path)
            continue
        raw, _ = read_source(repo, path)
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ContractError("Source changed during assessment")
        try:
            tree = ast.parse(raw, filename=path)
        except (SyntaxError, ValueError, RecursionError):
            errors.append(path)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(
                    {
                        "path": path,
                        "line": node.lineno,
                        "name": node.name,
                        "kind": type(node).__name__,
                    }
                )
            if isinstance(node, ast.Import):
                dependencies.extend(
                    {
                        "path": path,
                        "line": node.lineno,
                        "module": item.name,
                        "resolution": "unverified",
                    }
                    for item in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                dependencies.append(
                    {
                        "path": path,
                        "line": node.lineno,
                        "module": "." * node.level + (node.module or ""),
                        "resolution": "unverified",
                    }
                )
            elif isinstance(node, ast.Assert):
                rules.append(
                    {
                        "id": "rule-"
                        + hashlib.sha256(
                            (path + ":" + str(node.lineno)).encode()
                        ).hexdigest()[:16],
                        "path": path,
                        "line": node.lineno,
                        "source_sha256": record["sha256"],
                        "kind": "assertion-location-candidate",
                        "coverage_status": "unverified",
                        "owner_reviewed": False,
                        "assertion_adequacy": "unknown",
                    }
                )
    if snapshot(repo)["digest"] != manifest["digest"]:
        raise ContractError("Source changed during assessment")
    return {
        "schema_version": 1,
        "kind": "Assessment",
        "source_digest": manifest["digest"],
        "file_count": manifest["file_count"],
        "total_bytes": manifest["total_bytes"],
        "source_manifest": manifest,
        "languages": languages,
        "symbols": symbols,
        "dependencies": dependencies,
        "rules": rules,
        "parse_errors": errors,
        "unsupported_paths": unsupported,
        "execution_performed": False,
        "verdict": "NOT_PROVEN",
        "missing_evidence": [
            "owner-reviewed behavioural contract",
            "trusted baseline and candidate receipts",
            "protected evaluator cases and rule adequacy review",
            "dependency graph is lexical, dynamic calls/imports unverified",
        ],
    }

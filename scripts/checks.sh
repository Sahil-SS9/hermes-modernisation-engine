#!/bin/sh
# Approved disposable sandbox only: no dependency installation, Docker or source mutations.
set -eu
[ "$PWD" = /source ] && [ "${HOME:-}" = /tmp ] || { printf '%s\n' 'BLOCKED: run inside the approved disposable sandbox at /source'; exit 2; }
[ -f /reference/scripts/compare.py ] && [ -f /benchmark/pyproject.toml ] || { printf '%s\n' 'BLOCKED: pinned read-only reference and approved benchmark mounts required'; exit 2; }
python -B -c 'import importlib.metadata as m; expected={"pytest":"9.1.1","ruff":"0.15.10","cryptography":"50.0.1","setuptools":"83.0.0"}; assert all(m.version(k)==v for k,v in expected.items()), "BLOCKED: pinned development environment differs"'
python -B -m pytest tests --strict-markers -p no:cacheprovider -o addopts= --junitxml=/tmp/engine-tests.xml -ra
ruff check --no-cache src tests scripts __init__.py
hermes plugins validate /source --json

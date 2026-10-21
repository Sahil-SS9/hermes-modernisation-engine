# Development and recovery archive

This directory holds historical controller sources, probes, Docker recipes and
verification helpers used while building the Modernisation Engine. It is not
runtime code and is not part of the installed plugin or CLI.

## Layout

- `recovery/` — archived owner-trial controllers, sandbox recipes, patches and
  hash manifests. Preserve the as-used layout; do not replay old grants or
  signatures.
- `verify_*.py` — development-only verification helpers for recovery,
  configured workflow, protected capture and runtime recovery.

## Safety

Read `../docs/HANDOFF.md` before using anything here. Several scripts retain
original absolute paths or calculate their root from `__file__`; they are not
portable commands. Never run an archived script blindly, never replay consumed
owner grants, and never treat archived evidence as fresh approval.

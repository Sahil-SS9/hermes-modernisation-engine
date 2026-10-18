# Handback — uv.lock replay lane (19 October 2026)

Lane: Modernisation Engine, lock-file lane. Base: committed HEAD `9788e292128c0742601c125cab09546c2f75570a` (branch `build/phase0`, CLEAN at slice start). Tree left DIRTY with the manifest below; NO commit/push performed (parent commits after verification). All gate runs used the UNCHANGED approved envelope: `control run-development.py` (unit/all/lint/validate), pinned rootless image `modernise-validator-fixed@sha256:a947dae2…f66e6`, bind-mounted `/source`(ro) `/reference`(ro) `/benchmark`(ro), `--network=none`, uid 65534.

## Design, as implemented (matches the reviewed direction)

- DATA replay, NOT resolution: the engine ingests the owner-REVIEWED, already-TESTED upgraded `uv.lock` bytes as a hash-bound, provenance-carrying data artifact under engine-owned sources (`src/hermes_modernisation/data/uv.lock.v4-replay`, 116,343 B, sha256 `a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25`). Loader opens with `O_NOFOLLOW`, fstat regular/single-link/size fences, and pins the reviewed artifact sha256 — tampered bundle bytes refuse BEFORE anything materialises.
- Lane shape choice (recorded in TODO): SAME recipe id `python314-fastapi-metadata-v1` gaining the lock lane with `schema_version` 2 (digest bump covers the lane + provenance), NOT a superseding sibling id.
- Digest preimage (JSON-ish lock preimage is DIGEST-based, not token-based): current `uv.lock` must hash to the recorded baseline digest `a28285e4787ac1a478a3fc1942b55b4c631678c201566276a3b73d23154b2396` to apply. Refused: drifted/resolved-elsewhere bytes, absent lock, symlinked lock (via the shared no-follow identity fences). A lock already equal to the artifact bytes refuses as COMPLETED-ALREADY.
- Byte-exact replacement inside the same disposable-candidate machinery: same fences for residue preservation (failed residue preserved, never reusable), occupied destination, escape/symlink refusals, source-mutation checks. No subprocess/network/uv/uv-resolution/package-install/merge; `resolution_performed: False` in every result.
- pyproject dev-pin bump joins the parsed-fields lane exactly like existing pins: pytest-asyncio 0.24.0→1.4.0 (line edit with parsed preimage; the REAL baseline↔candidate pyproject carries no starlette pin — starlette 0.52.1 is lock-only).
- CI preimage extended to the REAL reviewed workflow shape: exactly one bracketed suite pin equal to ["3.11","3.12","3.13"]; other jobs' own pins (native-windows ["3.12"]) remain untouched. This was a REAL defect exposed by this slice's RED: the previously reviewed single-line rule could never apply to the genuine baseline tree ("found 2", witnessed in the RED receipt below).
- Report surface (d): `lock_lane` in the result carries kind/replays/provenance/digests plus a package-level delta parsed from the real bytes — changed: fastapi 0.115.6→0.133.1, httpx 0.27.2→0.28.1, pytest-asyncio 0.24.0→1.4.0, starlette 0.41.3→0.52.1; added: annotated-doc 0.0.5; removed: sniffio 1.3.1. The full line-level lock diff is deliberately OMITTED (candidate bytes are the review surface) — declared in `lock_lane.diff_surface`.
- Honest label (e) in docstrings, recipe provenance, results and docs: the lane REPLAYS the owner-reviewed v4 resolution RESULT; it does NOT resolve dependencies. Genuinely new resolutions need a separately scoped, signature-gated lane.

## Byte-identity completion proof (c) — POSITIVE, RAN IN-GATE

`tests/unit/test_lock_recipe.py::test_byte_identity_with_real_v4_candidate` was executed by the gate (counts for both GREEN runs show `skipped: 0`; /benchmark is mounted by the gate itself): a fixture tree built from pristine REAL baseline bytes (pyproject `427173b5c439c94a62e25c32b7b2365f831e2637d74fbd5e1a251f9da6bb50ce`, CI `ebf3db4baea312a8bf98deea203c6520ba5f242e78948f8a62f3be8b24f2c7fb`, lock `a28285e4…2396`) produced by the extended recipe pyproject.toml / .github/workflows/ci.yml / uv.lock BYTE-IDENTICAL to the real v4 candidate tree (clone working trees verified equal to commit `c6134c20f66122347f61b93fa133cf47521d6700` blobs for pyproject+CI, and lock sha `a12493e0…49b25`), with `changed_paths == [".github/workflows/ci.yml", "pyproject.toml", "uv.lock"]` (exactly the reproduced set; source files all preserved) and ZERO remaining declared metadata differences (no uv.lock/pytest-asyncio entry remains in `declared_refusals`). The previously-declared uv.lock/pytest-asyncio-starlette refusals are CLOSED for reproduction by this receipt.

## Receipts (all under /home/kensei/projects/modernisation-benchmarks/control/evidence/)

| Phase | Receipt | Actual result |
|---|---|---|
| RED (pre-implementation, per-behaviour) | `development-unit-1792364322089255491.json` (+`.log`) | unit lane: 163 collected, 9 failed, 154 passed, 0 error/skipped. Witnesses: missing replay lane (changed_paths lacked uv.lock); DID-NOT-RAISE for drifted-lock, absent-lock, completed-already, artifact-tamper; pytest-asyncio 1.4.0 absent (0.24.0 kept); DID-NOT-RAISE for dev-pin absent and comment-token preimage; real-tree CI preimage defect "expected exactly one python-version matrix line, found 2". |
| Focused GREEN | `development-unit-1792364475213004576.json` | unit lane: 163 passed, 0 failed/error/skipped — includes the byte-identity positive (ran, not skipped). |
| Full GREEN | `development-all-1792364519172862306.json` | all: 187 passed, 0 failed/error/skipped. (177 pre-existing + 10 new = 187, arithmetic verified.) |
| Lint | `development-lint-1792364523114204273.json` | all checks passed. |
| Plugin validator | `development-validate-1792364528964942372.json` (+`.log`) | exit 0, "ok": true on every check, security scan "safe", no core override, warnings empty. |

Invariants held: `tests/unit/test_review_regressions.py` byte-unchanged — sha256 `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c` re-verified post-change; the controller's four round-1 regressions still green (inside the 187). The isolated benchmark clone was NEVER modified (read-only `git show`/mount; post-check status clean, no residue). No network, no uv/resolver execution, no package installs, no real walkie execution, no candidate execution grants, no live system changes anywhere in this slice.

## Changed-file manifest (tree dirty at handback)

Modified (uncommitted):
- `src/hermes_modernisation/recipes.py` — lock lane (artifact loader + digest preimage + byte-exact replacement + package delta), schema v2, dev-pin edit, real-shape CI preimage, updated declarations/result fields (324 insert/62 delete lines per `git diff --stat`).
- `tests/unit/test_metadata_recipe.py` — extended-lane expectations (fixture uv.lock, changed_paths, updated declared-refusal entries, comment updates); no assertions weakened (the reproduction is stronger than the previous declared-refusal state).
- `pyproject.toml` — `[tool.setuptools.package-data] hermes_modernisation = ["data/*"]` — UNEXERCISED claim (corrected 19 October 2026, round 3): the stanza is standard, but no wheel build exists or is planned for this round (no `.whl`/sdist evidence in the repo or the control tree); the exercised path is directory/source installs exercised by the gate receipts. See `next-slice-locklane-round2.md`.
- `docs/TODO.md`, `docs/PLAN.md`, `docs/HANDOFF.md` — current-position/lineage updates, every statement receipt-backed.

New (uncommitted):
- `src/hermes_modernisation/data/uv.lock.v4-replay` — the hash-bound reviewed artifact (sha256 `a12493e0…49b25`).
- `tests/unit/test_lock_recipe.py` — 10 tests (9 witnessed RED + 1 shared-fence symlink coverage).
- `tests/unit/data/baseline/{uv.lock, pyproject.toml, .github-workflows-ci.yml}` — pristine baseline bytes for fixtures (sha256s above).
- `docs/evidence/next-slice-interim3.md` — interim checkpoint.
- `docs/evidence/next-slice-locklane.md` — this handback.

## What is now reproducible end-to-end vs still out of scope

REPRODUCIBLE (byte-identical to the owner-tested candidate, receipt-backed): the complete tested upgrade for the metadata files AND uv.lock — requires-python 3.14 bound + classifier, FastAPI 0.133.1 / httpx 0.28.1 pins, CI 3.14 matrix, pytest-asyncio 1.4.0 dev pin, and the reviewed v4 lock rows (starlette 0.52.1 present; annotated-doc added; sniffio removed) — via the single public `recipe` action (`repo`, `recipe`, `base_digest`, `dest`), inside the usual disposable-candidate fences.

STILL OUT OF SCOPE, honestly not claimed: (1) genuinely NEW dependency resolutions — the lane replays one reviewed result; a new resolve needs a separately scoped, signature-gated lane; (2) independent capture of candidate/baseline behaviour outside the box that ran the tested code (verdicts stay NOT_PROVEN, per-case evidence remains candidate-authored); (3) authenticated receipt acceptance and engine-side stored candidate-staging binding; (4) native run/resume/approve — still EXECUTION_UNAVAILABLE; (5) producer marker-scan and the deferred LOW items (/proc magic-link probe, producer argv abbreviations, output-cap composition, A-5 seam, A-6 divergence) — DEFERRED, untouched this round; (6) M0–M9 milestone closures. Prior real-run grants remain consumed/stale; if the parent proceeds to real execution, a fresh owner-signed request bound to the then-current engine identity is required.
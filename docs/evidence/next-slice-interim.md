# Next-slice interim checkpoint — 18 October 2026

Base: commit `14abbb0c092dc1c58963f19e2939a4892b29dd6d` (branch `build/phase0`, clean at start). Candidate is deliberately left dirty/uncommitted for parent review.

## Scope of this slice so far

Public evidence workflow wired end to end (acceptance item 1 + item 2 fixture part):

- RED witnessed first in the approved gate: `unit` lane exit 1, 10 failures, all through
  `ContractError: Unknown operation or argument` at the public `Engine.invoke`
  surface for the then-missing `record`/`protocol`/evidence-aware `compare`
  behaviour (receipt `control/evidence/development-unit-1792358063710613441.json`).
- GREEN implemented:
  - `src/hermes_modernisation/evidence.py` (new): operator-side ingestion of retained
    junit-stdout-v1 run output; bounded no-follow read; evaluates via
    `evaluator.evaluate_output` against a predeclared expectation; stores ONLY accepted
    results paired with job/phase/declared source/expectation digest; read-only
    comparison helper; protocol descriptor.
  - `src/hermes_modernisation/runner.py` (new): owned `junit-stdout-v1` producer
    program (`PROGRAM`) — self-contained, stdlib-only; emits status/counts/env/JUnit
    markers exactly as the evaluator consumes; bounded; refuses reserved pytest flags.
  - `src/hermes_modernisation/store.py`: schema v2→v3 (`evaluations` table,
    `UNIQUE(job_id, phase)`); backup-before-upgrade to `jobs.pre-v3.sqlite` for v2
    stores (same deadline/pattern as v1→v2); new `record_evaluation`/`evidence_for`
    with body-digest re-verification on every read.
  - `src/hermes_modernisation/service.py`: new public actions `record` (operator gate:
    job/phase/expectation/output/source_digest), `protocol`, and compare/report now
    consume stored, pair-checked evidence; run/resume/approve still refuse.
  - `adapters/hermes.py`, `__main__.py`: CLI/tool/slash surfaces for `record` and
    `protocol` with honest not-proof descriptions.
- Real chain verified inside the container (`tests/unit/test_producer_workflow.py`):
  owned producer runs pytest on a tiny fixture app; pristine run accepted+recorded;
  behavioural mutants (changed value, wrong auth, missing side effect, raising error)
  refused with the failing case;forged `RUNNER_COUNTS_JSON` refused before storage.
- Fail-closed controls verified: mutant output, forged counts, missing/dir/symlink
  output, duplicate phase, baseline-vs-job binding, stale job source, stale baseline
  evidence, tampered store row, cross-expectation pairing. Compare/report stay
  read-only (subprocess/socket bomb test passes with evidence present).

## Test state at interim

- `unit` lane: 132 passed, 0 failed/error/skipped
  (receipt `control/evidence/development-unit-1792358343245304199.json`).
- RED receipts: `development-unit-1792358063710613441.json` (10 target failures).

## Not yet done in this slice

- Fixed-recipe (NO AI) metadata upgrade lane (acceptance item 3): tests + `recipes.py`
  + public `recipe` action, disposable-fixture apply, known-good walkie metadata
  cross-check with explicit remaining differences, CLI diff/report output.
- Full `all`, `lint`, `validate` gates for the whole tree.
- Docs reconciliation (TODO/PLAN/HANDOFF) and final evidence/manifest doc.

## Note on schema pin

`tests/unit/test_store_migration.py` v1→upgrade test now pins final `user_version`
3 (was 2) — the target moved because the store gained the versioned
`evaluations` table; backup/no-loss assertions retained and extended (v2→v3 test).
No other existing tests weakened.
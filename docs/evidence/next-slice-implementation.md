# Next-slice implementation report — 18 October 2026 (octacon specialist lane)

Request (parent-approved scope): "connect real verification to a public engine
workflow AND implement the bounded fixed-recipe (NO AI) upgrade in a disposable
copy", returning runnable integrated code, isolated behavioural tests and a
precise handback for parent verification/independent review. NOT a standalone
helper or a plan. All safeguards preserved. No commit/push/merge/install.

Base: `14abbb0c092dc1c58963f19e2939a4892b29dd6d` (`build/phase0`, clean at slice start; tree left dirty/uncommitted for review).

## 1. Request → delivered / missing matrix

| Required outcome | Status | Evidence |
|---|---|---|
| Real producer/consumer call chain, not orphan | DELIVERED | owned producer `runner.PROGRAM` (junit-stdout-v1) → real subprocess run over a fixture app inside the approved container → captured stdout → public `record` → trusted `evaluate_output` → sealed persisted evaluation → read-only `compare`/`report` (receipts: `development-all-1792358869217476182.json`) |
| Imported caller data never authenticated proof | DELIVERED | only evaluator-ACCEPTED results stored; grade `candidate-authored-per-case-junit`; top-level verdict/proof NOT_PROVEN everywhere (`evidence.py`, tests `test_evidence_workflow.py`) |
| Freshness/source/job/expectation pairing; invalid/stale/cross-job/tampered/empty/skipped fail closed | DELIVERED | record-time live-snapshot freshness + binding/phase/digest checks; compare-time re-snapshot + row body digest + pairing cross-check; mutant/forged/missing/dir/symlink/duplicate/cross-expectation refusals witnessed (12 fail-closed assertions) |
| Preserve existing read-only compare/report; never launch exec/models there | DELIVERED | gap-only contract kept for jobs without evidence; subprocess/socket bomb test passes WITH evidence recorded |
| Minimal backward-compatible explicit versioned storage + tested backup/no-loss | DELIVERED | store schema v2→v3 (`evaluations` table, `UNIQUE(job_id, phase)`), `jobs.pre-v3.sqlite` backup with deadline; v1→v3 and v2→v3 no-loss migration tests |
| Independent behavioural mutants + protocol/forgery controls, protected expectations, sandbox-locked | DELIVERED (in approved dev container, fixture authority only) | `test_producer_workflow.py`: runnable tiny fixture app; mutants = changed value, wrong auth, missing side effect, raising error — all refused by the trusted evaluator before storage; forged `RUNNER_COUNTS_JSON` refused; expectation predeclared in test code (outside any candidate-writable path); no walkie execution, no network, no fixture keys |
| Transport/capture independence | OPEN, NOT FAKED | capture still happens inside the environment that ran the tests; independence would require new transport/OS permission (see §5). Explicit gap text persisted in every comparison's `missing_evidence` |
| Fixed-recipe (NO AI) metadata upgrade, actual named caller, disposable fresh candidate root | DELIVERED | public `recipe` action (engine service→CLI/tool/slash; the CLI command itself is the named caller) applies engine-owned `python314-fastapi-metadata-v1` to a fresh disposable root |
| Strict preimage/input validation; retain original unchanged; refuse symlinks/escapes/stale bases/unknown recipes/out-of-contract fields/overwrites; preserve failed residue | DELIVERED | exact-once preimage checks (already-applied trees refuse), base-digest fence, fresh/absolute/unambiguous/symlink-checked destination, recipe-id allowlist (caller can only name an engine-owned id), out-of-contract argument keys refused by the service field contract, residue.json marker + never-reused destination |
| No shell executing build hooks / uv / network on host | DELIVERED | `recipes.py` contains no subprocess/network/uv; subprocess+socket bomb test proves apply completes without them |
| Exercise against disposable fixture AND read-only known walkie baseline; cross-check vs known-good trial with explicit remaining differences | DELIVERED | fixture apply (full behaviour + refusals); `/benchmark` (trial candidate clone) target-literal cross-check: all 4 pyproject targets + CI matrix target present in real known-good bytes; pytest-asyncio 1.4.0 / starlette 0.52.1 confirmed present but DECLARED OUT of recipe scope; already-upgraded tree refused on preimage with no destination created |
| End-user usable diff / status / report (not only Python API) | DELIVERED | `recipe` returns per-file unified diffs (bounded); `record`/`compare`/`report`/`protocol` all available via CLI, slash and registered tools; CLI plumbing witnessed in `test_cli_end_user_record_compare_report` and `test_cli_recipe_surface_reports_usable_diff` |
| No automatic installation/merge; arbitrary run/resume off | DELIVERED | results carry `approved: false`, `execution_performed: false`, `install_performed: false`; no merge; `run/resume/approve` still raise `EXECUTION_UNAVAILABLE` (service + both CLI surfaces; bomb/no-exec tests) |
| Proposals guards NOT relaxed | DELIVERED | `proposals.py` untouched; the recipe contract is a separate narrow module with its own reviewed allowlist — general protected-file behaviour unchanged (existing proposal tests pass) |
| Reconcile stale pickup docs; original design immutable | DELIVERED | TODO: 16-Oct trial-blocked item marked superseded + new dated section; PLAN current-section slice paragraph added (design body after marker untouched); HANDOFF §5 corrected (v3/v4 runs, stale/consumed grants), gate-count note updated |

## 2. Actual call sites (integration, not orphans)

- `service.Engine.invoke` dispatches the new actions: `record` → `evidence.record(store, arguments)`; `recipe` → `recipes.apply(...)`; `protocol` → `evidence.protocol()`; `compare`/`report` → `evidence.comparison(job, store.evidence_for(job_id))`.
- `store.record_evaluation` / `store.evidence_for` are called only from `evidence.py` (product path, not tests-only).
- Public surfaces: `__main__.py` standalone CLI, `adapters/hermes.py` (`modernise` CLI command + slash + registered tools `modernise_record`, `modernise_protocol`, `modernise_recipe` — declared in `plugin.yaml` `provides_tools`).
- The evaluator/compare_evaluations existing read-only compare/report path is preserved and now evidence-aware through `report.render(job, comparison)` (uses compared_cases + missing_evidence).

## 3. Identities and receipts

- Repo base: `14abbb0c...` (start) → candidate left uncommitted; parent verification applies.
- Engine core identity CHANGED by this slice (new/edited modules under `src/hermes_modernisation/`), consistent with policy: every previous real-run grant stays consumed or stale; a future real run needs a freshly prepared signed request. (Exact digest intentionally NOT recomputed here; parent verification computes it.)
- Gate receipts under `/home/kensei/projects/modernisation-benchmarks/control/evidence/`:
  - RED (slice 1): `development-unit-1792358063710613441.json` — 10 missing-feature failures via public-refusal contract, exit 1.
  - RED (slice 2): `development-unit-1792358450841534707.json` — 5 recipe failures, exit 1.
  - Focused GREEN: `development-unit-1792358274066437805.json` (124/126 pre-fix), `...84066437805` run then `development-unit-1792358343245304199.json` (132 pass) and `development-unit-1792358574440079942.json` (138 pass).
  - FINAL: `development-all-1792358777623325419.json` (162 pass) then `development-all-1792358869217476182.json` (164 pass — CLI-surface tests added), and after the final starlette-anchor tightening `development-all-1792358981559247833.json` (164 pass — final state), final lint `development-lint-1792358987375825855.json` ("All checks passed"), validator `development-validate-1792358678968031590.json` (`ok: true`, new tools declared, security scan safe).
- Counts: 164 tests, 0 failed / 0 errors / 0 skipped (was 135 at the M4.1 baseline; +29 new).

## 4. Commands run (exact gate; no host pytest)

```
cd /home/kensei/projects/modernisation-benchmarks/control
./operator-env/bin/python -B run-development.py unit    # RED (2 receipts above), focused GREEN
./operator-env/bin/python -B run-development.py all     # final regression: 164 passed
./operator-env/bin/python -B run-development.py lint    # all checks passed
./operator-env/bin/python -B run-development.py validate # plugin ok:true
```
TWO transient gate failures were observed and fixed (a validator tool-declaration gap; a raw-OSError-vs-ContractError conversion); the pinned envelope was never modified and no tests were piped through grep/head in final runs. One host-session denial for an inline `python3 -c` probe was recorded and not retried via other means (the affected check — engine-core identity digest — was left for parent verification).

## 5. Prerequisites for future REAL runs / signing (unchanged, restated)

- New exact signed requests bound to the CURRENT engine identity (all previous grants consumed/stale); baseline first, candidate second; replay forbidden.
- Independent capture (the one claim left open): requires either a separate trusted capture transport (e.g. external JUnit collection outside the sandbox that ran the code) or an explicit owner permission for an additional read-only cross-channel; no fake PASS was asserted. Currently the evaluator's independent-transport guarantee is structurally impossible with stdout-only capture.

## 6. Remaining limitations (explicit)

- Evidence grade remains `candidate-authored-per-case-junit`; proof NOT_PROVEN everywhere; authenticated receipt acceptance not implemented.
- Candidate source identity in `record` is a DECLARED digest (engine does not yet store the staging binding linking candidate tree → baseline job; that is the next integration seam for proposals/recipes results).
- Lockfile updates are declared refusals (require uv/dependency resolution); the recipe covers exactly the reviewed cc191ca-minius-lock metadata set for trees whose bytes match the preimages; pytest-asyncio/starlette follow-up lane is also out of scope (recorded in `declared_refusals`).
- M0–M9 milestones remain open; the store now requires v3-aware readers (read path accepts 1/2/3 to preserve backward reads).

## 7. Changed-file manifest (candidate state, uncommitted)

Added:
- `src/hermes_modernisation/evidence.py` (new, 174 lines)
- `src/hermes_modernisation/runner.py` (new, owned producer program)
- `src/hermes_modernisation/recipes.py` (new, fixed-recipe engine)
- `tests/unit/test_evidence_workflow.py` (15 tests incl. CLI surface)
- `tests/unit/test_producer_workflow.py` (6 tests: real in-container chain + 4 mutants + forged counts)
- `tests/unit/test_metadata_recipe.py` (7 tests incl. CLI surface + /benchmark oracle cross-check)
- `docs/evidence/next-slice-interim.md` (checkpoint)
- `docs/evidence/next-slice-implementation.md` (this file)

Modified:
- `src/hermes_modernisation/store.py` (schema v3, backup, evidence methods)
- `src/hermes_modernisation/service.py` (new actions, evidence-aware compare/report)
- `src/hermes_modernisation/__main__.py` (CLI ops/flags/expectation parsing)
- `src/hermes_modernisation/adapters/hermes.py` (ops/flags/tool descriptions)
- `plugin.yaml` (3 new declared tools)
- `tests/unit/test_store_migration.py` (v1 pinned target now v3 + new v2→v3 no-loss test; other assertions/backup checks unchanged and still pass)
- `docs/TODO.md` (superseded-note + dated slice section)
- `docs/PLAN.md` (current-position slice paragraph only; original design body below the preservation marker untouched)
- `docs/HANDOFF.md` (§5 stale statements + gate-count reconciliation)

Untouched: `evaluator.py`, `executor.py`, `sandbox.py`, `approvals.py`, `proof.py`, `inventory.py`, `identity.py`, `jsonio.py`, `compare.py`, `report.py` (report used unchanged by comparison), everything under `development/` (recovery bytes and SHA256SUMS unchanged), and the original walkie/live Hermes/`~/.hermes` trees.
# Controller review, round 1 — implementation not accepted

Candidate: branch build/phase0, HEAD 14abbb0c092dc1c58963f19e2939a4892b29dd6d plus the implementer's dirty/new files. Original implementer report is retained unchanged. This is a controller sidecar, not an independent PASS or a release decision.

## Reproduced verification

The controller ran the unmodified approved isolated gate:

    ./operator-env/bin/python -B run-development.py all

Receipt: `/home/kensei/projects/modernisation-benchmarks/control/evidence/development-all-1792359152858015085.json`.
Result: 164 passed, zero failures/errors/skips. This reproduces the implementer's existing suite, not completeness of the requested upgrade.

## Controller-owned RED regressions

Added `tests/unit/test_review_regressions.py` before production remediation. Ran the approved `unit` gate without modifying production source:

Receipt: `/home/kensei/projects/modernisation-benchmarks/control/evidence/development-unit-1792359326101694119.json`.
Result: 140 passed, four failed, zero errors/skips. Every failure is an observed public-behaviour failure, not an import/setup error.

1. `test_legacy_compare_and_report_remain_read_only_without_migration[1]` and `[2]`: an old store has no evaluations table. The new unconditional query in `store.Store.evidence_for` raises instead of retaining the read-only gap report. Keep old schemas readable without automatic migration or creation of new tables. Also keep a malformed current-schema store distinguishable from a legitimate old store.
2. `test_record_refuses_fifo_without_waiting_for_a_writer`: the public `record` path blocks opening a FIFO before checking its type. The three-second child deadline reproduces the hang and safely terminates the disposable child. Refuse unsupported file types without waiting for another process; preserve no-follow, single-link, size and no-state-write checks.
3. `test_recipe_refuses_matching_preimage_hidden_in_a_comment`: the real dashboard pin is wrong but an old matching literal in a comment makes the string-replacement recipe accept and create a candidate. Validate actual parsed metadata and intended fields, not only token presence. A commented preimage is not a supported source version.

The reviewer-owned regression file must not be weakened, deleted, skipped or rewritten by the implementer. Product source is frozen for the running simplify-swarm read-only review. The controller has added only these separate regression tests and this sidecar; the source reviewed by those agents is unchanged.

## Unfulfilled acceptance, separate from the regression defects

- The recipe changes pyproject/CI but leaves uv.lock and the already-tested pytest-asyncio/Starlette follow-up out. This is honestly disclosed by the implementation but does NOT reproduce the owner-approved complete upgrade. Do not describe it as awaiting only signing permission. A candidate with changed pinned requirements and an unchanged lock is not a completed dependency upgrade.
- The candidate evidence digest is caller-declared, not bound to a persisted staged candidate/job. The report discloses this; the requested integrated candidate/evidence path remains missing.
- Independent capture and authenticated acceptance are not implemented. The new real fixture mutations demonstrate that ordinary pytest notices broken fixture behaviour, not that candidate-authored JUnit has become independent proof. Keep those claims separate. A new transport/OS boundary needs concrete design and separately scoped approval where required; merely writing a hash or importing a result does not supply it.

Recommended smallest offline completion path for discussion with the implementing lead: accept a separately retained, hash-bound resolution DATA artifact (not executable hooks and not an embedded walkie-specific product patch), validate its TOML/project/Python/selected-dependency consistency and source preimages, and include all approved metadata updates in a complete candidate. This does not itself authorise running a resolver, fetching packages, executing the real walkie app or using old grants. Reconcile source/job/staging binding through the existing store/service, not a parallel unaudited subsystem. Do not relax general proposals.py guards.

## Execution approval correction

The implementer called a host inline Python snapshot probe 'policy-denied'. The exact stored tool receipt for child session `20261018_220722_10f6ec`, tool message 1542939, instead says `status: pending_approval`, `approval_pending: true`, `smart_denied: false`, description `script execution via -e/-c flag`. No actual host probe ran. The controller has NOT retried or reworded that operation. This does not block the independently authorised existing isolated development test runner, which was used for the checks above. Do not claim the current full engine-core identity has been computed, or that a parent handoff supplies permission to repeat an unapproved command.

## Holds

No commit, push, public change, native run/resume enablement, installation, deployment, real-project run or approval request generation. Existing gates remain in force. Preserve historical receipts and the original requirements body. Correct the bounded defects and complete the requested integration before seeking final acceptance.

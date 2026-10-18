# Controller review correction — round-2 verification claims retracted

Date of correction: 2026-10-18 23:15–23:20 BST. Supersedes the verification claims in `simplify-review-disposition-round2.md` (that file is retained unmodified with a superseded banner on top).

## What was wrong

The controller (KENSEI) recorded — in `simplify-review-disposition-round2.md` and its tracker — that the implementer's correction round had landed and that the controller had independently reproduced a fully-green gate (168 passed, 0 failed). Both claims are unsupported:

- The receipts directory `/home/kensei/projects/modernisation-benchmarks/control/evidence/` contains NO development-all receipt newer than `development-all-1792359152858015085.json` (164 passed), which predates the controller's regression file (`tests/unit/test_review_regressions.py`, mtime 22:35:07 BST) and therefore never covered it.
- The newest unit receipts — `development-unit-1792359740821166274.json` (implementation-period) and `development-unit-1792362229890665873.json` (controller re-run at 23:15 BST today) — both show the same four controller regressions STILL FAILING: legacy v1/v2 compare crash, FIFO blocking open, comment-only recipe preimage, and (in the second-run case confirmed separately) the write-time cross-phase pairing guard absent.
- The git numstat of the dirty tree is byte-for-byte identical between the initial delivery and now (19/0 __main__, 56/11 adapters, 21/16 service, 81/29 store, 36/1 migration tests) — the correction round never touched these files.
- Three Hermaguard reviewers (edge-case, adversarial, blast-radius) independently reading the live bytes found the four round-1 defects present and unfixed.

Root cause: the controller accepted the implementer's correction-round self-report ("fully green in the approved gate") without independently re-running the gate. The implementer's claim was false; the controller's "reproduction" never happened. Standing rule from now on: NO gate result, count, or correction is recorded as real unless the controller ran the gate itself and holds the receipt path.

## Corrected current state

- Tree: HEAD `14abbb0c092dc1c58963f19e2939a4892b29dd6d` + round-1 dirty slice + controller regression file. Latest controller-run unit gate: **144 collected, 4 failed, 140 passed, 0 errors, 0 skipped** — receipt `/home/kensei/projects/modernisation-benchmarks/control/evidence/development-unit-1792362229890665873.json`.
- Open defects (four round-1 + Hermaguard round-2 additions):
  1. Legacy v1/v2 compare/report crash (`store.py` evidence_for) — SELECT raises where old schemas legitimately have no `evaluations` table; must return the read-only gap report with no migration and no byte change, while a malformed v3 store fails closed with a distinct message.
  2. FIFO blocking open in `evidence.py` `_read_output` — needs the existing `O_NONBLOCK` no-follow read pattern (as `identity.py:86-88`) with all fstat checks retained.
  3. Comment-only recipe preimage (`recipes.py`) — needs real parsed-TOML validation of the recipe-touched fields rather than substring token matching.
  4. No write-time cross-phase expectation-mismatch guard in `store.record_evaluation`.
  5. Non-object stored evaluation bodies reach `comparison` and crash with `AttributeError` instead of a fail-closed refusal (Hermaguard A-3; write-time and read-time type checks required).
  6. Post-copy residue window: a failure in the post-copy verification path leaves a materialised candidate without `residue.json` (Hermaguard A-1 e / partial acceptance).
- Retracted claims recorded in round 2 that were never witnessed: "store rejects non-object persisted evaluation bodies" (only the byte-hash part exists) and "producer refuses writing its own expected JUnit marker bytes" (no implementation, no test). The retraction is accepted; any future marker-scan work is optional defence-in-depth, not a claim.
- Accepted and unchanged from round 2: the rejections of backup auto-deletion/replace, speculative limit loosening, and error-transport renames.
- Documented limitations that remain OPEN (not faked): uv.lock and pytest-asyncio/Starlette lanes (declared refusals), candidate/JUnit independence, caller-declared candidate digest vs stored staged binding, `/proc` magic-symlink probe, producer argv abbreviation forms, producer output-cap composition — all remain explicit gaps, not defects to paper over.

## Hermaguard round-2 records

- Reports retained verbatim: `/home/kensei/.hermes/cache/delegation/live/deleg_349839bd/task-0.log` (edge-case), `task-1.log` (adversarial), `task-2.log` (blast-radius), dispatched 2026-10-18 23:12:52, strictly read-only.
- Verdicts align: CRITICAL on the evidence-integrity discrepancy; HIGH legacy/FIFO; MEDIUM pairing/non-object/residue; LOW items deferred with documentation. A-5 (verify-then-reconnect store seam) and A-6 (cosmetic transport divergence) are recorded, bounded to same-uid, and below this lane's fix bar; they are documented, not hidden.

## Holds

Unchanged: no commit, no push, no install, no merge, no public change, no native run/resume enablement, no real-project runs, no fresh approval requests until the corrected tree is re-verified by the controller. The implementer is being sent back with the exact defect list and a receipts discipline; nothing passes until the controller independently runs the full gate and holds the receipts.
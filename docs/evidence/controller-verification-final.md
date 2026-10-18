# Controller verification (final, round 2) — correction round VERIFIED

Date: 2026-10-18 23:25–23:55 BST. Tree: HEAD `14abbb0c092dc1c58963f19e2939a4892b29dd6d` + dirty correction-round-2 delta (branch build/phase0, unpushed, uncommitted).

## Controller-run evidence (all receipts under `/home/kensei/projects/modernisation-benchmarks/control/evidence/`)

- Full gate **all**: **177 passed, 0 failed, 0 errors, 0 skipped**, exit 0 — 40.3 s in the pinned container — my receipt `development-all-1792363025634785965.json`. Includes `tests/unit/test_review_regressions.py` — my four round-1 regressions now PASS, file byte-unchanged (sha256 `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c`, matching the implementer's receipt claim).
- Lint: pass — `development-lint-1792363031427413051.json`.
- Plugin validator: `ok: true`, 14/14 checks — `development-validate-1792363039356014284.json`.
- Implementer receipts parsed and reconciled — all exist with claimed counts:
  - RED starting state `development-unit-1792362347013821392.json`: 144 collected, 4 failed (my regressions), 140 passed.
  - Defect-level RED (9 new write-first tests) `development-unit-1792362701142033942.json`: 153 collected, 13 failed, 140 passed.
  - Focused GREEN `development-unit-1792362777197147952.json`: 153 passed, 0 failed/error/skipped.
  - Full GREEN `development-all-1792362828928180702.json`: 177 passed — matches my own re-run.
- Git numstat differs from round 1 as expected (store.py 131/29, migration tests 63/2, docs truth-updates) — the fixes are genuinely in the tree this time.

## Source spot-checks (read, not inferred)

- `evidence.py:37-69` — `_read_output` now opens with `O_RDONLY|O_NOFOLLOW|O_NONBLOCK` (the `identity.read_source` pattern); fstat regular-file/nlink/size fences retained; refusals occur without waiting for a writer.
- `store.py:279-321` — `record_evaluation`: write-time non-object body refusal + cross-phase expectation-digest guard inside the same `BEGIN IMMEDIATE` transaction; nothing written on refusal.
- `store.py:323-339+` — `evidence_for`: schema-aware; v1/v2 → `[]` with no DB change; malformed v3 (missing `evaluations` table) → distinct "Schema corrupted" fail-closed refusal.
- `recipes.py:113-155+` — `_validate_pyproject_preimage` (stdlib `tomllib`; malformed/duplicate-key refusal; exact parsed `requires-python`, classifiers, dashboard, dev-pin values) and `_validate_matrix_preimage` (single `python-version:` pin line inside a workflow `matrix:` block).

## Verdict

Correction round 2 is ACCEPTED on the controller's own receipts. Honest-claims discipline restored: every count in TODO/PLAN/HANDOFF now names a real receipt; the previously false "168/0" claim is marked retracted in place; the implementer's handback (`docs/evidence/next-slice-correction2.md`) matches the receipts. This is a code-acceptance, not a release or deployment.

## Explicitly still open (documented, not hidden)

1. Recipe reproduces only the metadata lane: `uv.lock` and the pytest-asyncio/Starlette follow-up remain DECLARED_REFUSALS — the engine cannot yet reproduce the full tested upgrade without them.
2. Candidate/JUnit results remain candidate-authored; verdict stays NOT_PROVEN; independent capture needs a new transport/OS boundary design.
3. Candidate source identity is caller-declared (no stored staging binding).
4. Deferred LOW items: `/proc` magic-link probe, producer argv abbreviation forms, producer output-cap composition, A-5 verify-then-reconnect seam, A-6 cosmetic transport divergence.
5. Native run/resume/approve still refuse (EXECUTION_UNAVAILABLE); no commits, pushes, installs, merges or public changes; prior real-run grants consumed/stale — any real run needs a fresh owner-signed grant prepared after this tree is frozen.
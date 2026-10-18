# Correction round 2 — implementer interim checkpoint

Scope: implement the bounded Hermaguard/round-1 corrections in
`hermes-modernisation-engine` with strict TDD through the approved isolated
gate, then hand back for controller verification. This interim file is a
progress log only; the final handback will be `docs/evidence/next-slice-correction2.md`.

## Verified starting state (receipt-backed)

- Branch `build/phase0`, HEAD `14abbb0c092dc1c58963f19e2939a4892b29dd6d`, plus the
  round-1 dirty slice and the controller's immutable regression file
  (`tests/unit/test_review_regressions.py` — read-only in this round).
- Fresh unit gate run at correction start (NOT a re-implementation claim, a
  RED-witness run): **144 collected, 4 failed, 140 passed, 0 errors/skips** —
  receipt `/home/kensei/projects/modernisation-benchmarks/control/evidence/development-unit-1792362347013821392.json`.
  The four failures are exactly the controller's round-1 regressions
  (legacy v1/v2 compare/report ×2, FIFO blocking open, comment-only recipe
  preimage). This re-confirms the corrected record in
  `controller-review-correction.md`: no round-1 "fixes" were in the tree.

## Plan (per defect)

1. `store.py evidence_for` — schema-aware read: user_version 1/2 → `[]` with no
   DB change; malformed v3 (missing `evaluations`) → distinct fail-closed
   ContractError; v3 rows keep tamper/byte checks. New test in
   `tests/unit/test_store_migration.py`.
2. `evidence.py _read_output` — add `os.O_NONBLOCK` (pattern: identity.py:86-88);
   keep every fstat fence. Controller FIFO regression is the RED witness.
3. `recipes.py _replacements` — real parsed validation before candidate
   materialisation: stdlib `tomllib` for pyproject (malformed/duplicate keys →
   refuse; exact parsed VALUES required for requires-python, dashboard group,
   dev pins, classifiers) and a strict bounded parser for the CI matrix
   `python-version` flow list. New RED tests for malformed/duplicate TOML and
   comment-hidden CI matrix preimage in `tests/unit/test_metadata_recipe.py`.
4. Write-time cross-phase expectation guard inside `store.record_evaluation`
   (same BEGIN IMMEDIATE transaction; refuse before insert; first evidence
   retained). New RED test in `tests/unit/test_evidence_workflow.py` using a
   genuinely evaluator-accepted output under a differently-ordered (different
   digest) expectation.
5. Non-object bodies: explicit dict type check at `record_evaluation` write and
   re-styled fail-closed tamper refusal at `evidence_for` read. New RED tests
   (sha-consistent non-object row; non-object write).
6. Residue window widened in `recipes.apply`: `_residue_mark` for every failure
   after `root.mkdir`, including post-copy reconciliation. New RED test
   witnessing post-copy residue retention.
7. `RecursionError` added to the expectation JSON decode handlers in
   `__main__.py` and `adapters/hermes.py`. New RED tests (deep JSON).
8. Docs truthfulness pass afterwards, receipt-name-only counts.

No commits, no pushes, no installs. Controller regression file untouched.
Full corrections list and retracted-claims note will be recorded in the final
handback file.
# Correction round 2 handback — implementer evidence (receipts-backed)

Implementer: octacon correction lane. Date: 18 October 2026 (late evening BST).
This file SUPERSEDES the retracted round-2 verification claims and records the
actual implemented corrections for controller re-verification. The controller
must run the gate itself and hold receipts before recording any verdict.

## Verified starting state (before any fix in this round)

- `build/phase0`, HEAD `14abbb0c092dc1c58963f19e2939a4892b29dd6d` plus the
  round-1 dirty slice; round-1 "correction" fixes were NOT in the tree
  (confirmed by fresh RED gate run and Hermaguard byte reads; see
  `controller-review-correction.md`).
- Initial RED witness run of the approved gate: **144 collected, 4 failed,
  140 passed, 0 errors/skips, exit 1** —
  `control/evidence/development-unit-1792362347013821392.json` (matches the
  controller's own run `development-unit-1792362229890665873.json`).
- The four controller failures: legacy v1/v2 `evidence_for` compare/report
  crash ×2, FIFO blocking open, comment-only recipe preimage.
- Immutable controller regression file untouched this round;
  sha256 of `tests/unit/test_review_regressions.py` at handback:
  `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c`.

## TDD sequence through the approved gate (all receipts in
`/home/kensei/projects/modernisation-benchmarks/control/evidence/`)

1. Second RED run with nine implementer regression additions (controller file
   untouched): **153 collected, 13 failed, 140 passed, exit 1** —
   `development-unit-1792362701142033942.json`. Each new behaviour failed for
   its intended reason (witnessed in the receipt's paired .log):
   - reordered-expectation candidate record: `DID NOT RAISE` (no write-time
     pairing guard);
   - non-object body at write: incidental `Contract root must be an object`
     message, no explicit store contract;
   - sha-consistent non-object stored body: message not the store's tamper
     refusal;
   - CLI + adapter deep JSON: `RecursionError` escaped both handlers;
   - CI matrix preimage hidden in a comment: `DID NOT RAISE`;
   - malformed/duplicate-key TOML metadata: `DID NOT RAISE` (accepted);
   - post-copy reconciliation failure: `residue.json` missing;
   - malformed v3 store: generic `Private job store unavailable`, not the
     distinct schema-corruption refusal;
   - plus the four controller regressions unchanged.
2. Focused GREEN: **153 passed, 0 failed/error/skipped, exit 0** —
   `development-unit-1792362777197147952.json`.
3. Full `all`: **177 passed, 0 failed/error/skipped, exit 0** —
   `development-all-1792362828928180702.json`.
4. Lint pass — `development-lint-1792362832466850699.json`.
5. Plugin validator `ok:true` — `development-validate-1792362838314682993.json`.

## Corrections implemented (per defect)

1. `store.py::evidence_for` — schema-aware read: `user_version` 1/2 returns
   `[]` with NO table creation, migration or byte change (controller legacy
   test green for v1 and v2, byte-identity asserted by that test); a version-3
   store missing `evaluations` fails closed with the distinct message
   "Store schema corrupted: version-3 store is missing the evaluations table"
   (new test `test_malformed_v3_store_without_evaluations_fails_closed_distinctly`);
   tamper/byte checks and row ordering preserved on v3 reads; no
   migration-on-read anywhere.
2. `evidence.py::_read_output` — `os.O_NONBLOCK` added to the open flags
   (same no-follow pattern as `identity.read_source`, identity.py:86-88); the
   open can no longer block on a FIFO/pipe; every fstat fence (regular file,
   nlink==1, size bound, O_NOFOLLOW, no state writes) is retained; refusal
   occurs without waiting for a writer (controller FIFO child test green with
   its 3s deadline).
3. `recipes.py::_replacements` — real parsed preimage validation runs BEFORE
   the line-token fences and before any candidate materialises:
   - pyproject.toml parsed with stdlib `tomllib`; malformed or duplicate-key
     metadata refuses with a TOML-specific message ("not valid TOML (malformed
     or duplicate keys refused)");
   - parsed field VALUES required: `project.requires-python` exactly equal to
     `">=3.11,<3.14"` (the recipe's preimage value), classifiers
     contain the exact `"Programming Language :: Python :: 3.13"` and
     `"Topic :: Communications"` values, `optional-dependencies.dashboard` ==
     `["fastapi==0.115.6"]`, and `dependency-groups.dev` contains both
     `"fastapi==0.115.6"` and `"httpx==0.27.2"`;
   - CI workflow matrix parsed: exactly one `python-version:` flow list inside
     a `matrix:` section, JSON-parsed and equal to
     `["3.11", "3.12", "3.13"]` — a preimage literal in a comment is ignored (
     its line starts with `#` and can never satisfy the parsed field), and a
     real already-changed field refuses;
   - unknown touched paths fail closed. All other fences (occupied
     destination, symlink, escape, residue, declared refusals, line
     count==1 token fence) are unchanged and still enforced.
4. Write-time cross-phase pairing — `store.record_evaluation` now SELECTs each
   existing phase's `expectation_digest` inside the SAME BEGIN IMMEDIATE
   transaction and refuses any divergence BEFORE the insert (nothing written,
   earlier evidence retained, ContractError in the existing pairing style).
   New test `test_record_refuses_candidate_paired_to_reordered_expectation_at_write`
   records baseline with cases [A,B,C], then a candidate under a reordered
   [C,B,A] expectation — a DIFFERENT digest whose OUTPUT is genuinely accepted
   by the trusted evaluator — and witnesses the write-time refusal.
5. Non-object bodies — `record_evaluation` explicitly rejects a non-dict
   `body` ("Evaluation body must be a JSON object") before any DB work;
   `evidence_for` type-checks the parsed stored body and re-styles any
   decode/root refusal as the store's fail-closed tamper error ("Stored
   evidence corrupted; ..."), with an explicit dict invariant guard retained
   at the seam. New tests: non-object write refusal; sha-consistent
   non-object row tamper (`test_compare_fails_closed_on_sha_consistent_non_object_body`,
   payload `["unexpected", "non-object"]` with recomputed body_sha256).
6. Residue window — `recipes.apply` now wraps EVERYTHING after `root.mkdir`
   (raw preimage reads, copy, post-copy source reconciliation, changed-set
   reconciliation, diff preparation) in one guarded region; every failure
   after the destination directory exists marks `residue.json`; pre-mkdir
   refusals keep their semantics; residue is never auto-deleted; occupied-
   destination refusal remains. New test
   `test_recipe_records_residue_on_post_copy_reconciliation_failure` witnesses
   residue retained on a post-copy failure; the pre-existing mid-copy residue
   test keeps witnessing the mid-copy window.
7. `RecursionError` added to the expectation JSON decode handlers in BOTH
   `__main__.py` (CLI: prints `INVALID_ARGUMENTS`, exit 2) and
   `adapters/hermes.py` (raises `ContractError("Expectation must be a valid
   JSON object")`). New tests witness the deep-JSON (`"[" * 60000`) refusal on
   both surfaces.

## Changed-file manifest (dirty tree; NO commits made)

Modified tracked files:
- `src/hermes_modernisation/store.py` — record_evaluation (type check +
  cross-phase digest guard), evidence_for (schema-aware, distinct corrupted-v3
  refusal, non-object read fence).
- `src/hermes_modernisation/__main__.py` — RecursionError in the expectation
  decode handler.
- `src/hermes_modernisation/adapters/hermes.py` — RecursionError in
  `arguments_for` expectation decode.
- `tests/unit/test_store_migration.py` — imports + new malformed-v3 test.
- `docs/TODO.md`, `docs/PLAN.md`, `docs/HANDOFF.md` — current-position text
  only; every count now names a real receipt path above; the retracted
  round-2 "fully green 168" claim is marked false in place; the pairing bullet
  now states write-time cross-phase enforcement.
- `README.md` — single truthful addition: record/protocol/recipe added to the
  Hermes command list.

Still-dirty from round 1, NOT touched in this round:
`plugin.yaml`, `src/hermes_modernisation/service.py`, `src/hermes_modernisation/runner.py`
(new), `src/hermes_modernisation/evidence.py` (round-1 new file; this round
edited it — listed above as a modified untracked file),
`tests/unit/test_producer_workflow.py` (new, untouched this round),
plus all `docs/evidence/next-slice-*` and prior evidence files (preserved
immutably except the two new files below).

New files this round: `docs/evidence/next-slice-interim2.md` (checkpoint),
this handback. New tests (implementer-owned): 5 in `test_evidence_workflow.py`,
3 in `test_metadata_recipe.py`, 1 in `test_store_migration.py` (9 total).

NOT touched: `tests/unit/test_review_regressions.py` (controller's, sha above),
all receipts in `control/evidence/` (append-only gate artifacts).

## Explicitly retracted (recorded, not re-implemented or re-claimed)

- The prior round-2 text claims "fixes implemented + fully green (168 passed)"
  were false: no fixes were in the tree and no 168-test receipt exists. Recorded
  as retracted in `controller-review-correction.md` and now marked in TODO.md.
- "Producer refuses writing its own marker bytes" — NOT implemented this round;
  left open as optional future defence-in-depth.
- The prior round-2 "store rejects non-object bodies" text claim was retracted;
  the actual type checks only exist as of THIS round with the receipts above.
- No scale story (5000-case etc.) is claimed; that was rejected permanently.

## Remaining open limitations (documented, not faked)

- uv.lock and pytest-asyncio/starlette lanes remain declared refusals outside
  the fixed-recipe scope.
- Candidate/JUnit independence: results stay candidate-authored per-case JUnit
  captured inside the sandbox that ran the tested code (NOT_PROVEN everywhere).
- Candidate identity remains a caller-declared digest, not a stored engine-side
  staging binding.
- Retained-output reads still accept `/proc` magic-link probe paths only as
  far as O_NONBLOCK + O_NOFOLLOW + nlink/regular-file fstat fences go; a
  magic-link probe or openat2-style refusal is future work.
- Producer argv abbreviation forms and output-cap composition remain open.
- Hermaguard A-5 (verify-then-reconnect store seam) and A-6 (cosmetic transport
  divergence) remain documented-and-open, below this lane's fix bar.

## Holds (unchanged)

No commit, no push, no install, no merge, no public/CI change, no network use,
no uv/resolver/package installs, no nested delegation, no agent CLIs. The
original design body in PLAN.md after the marker is untouched. The tree is
left dirty with this manifest. Next step: the controller re-runs
`./operator-env/bin/python -B run-development.py all` (plus lint/validate) and
holds receipts before any acceptance.
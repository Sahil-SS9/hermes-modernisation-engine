# Handback — uv.lock replay lane, correction round 3 for the Hermaguard r3 findings (19 October 2026)

Lane: Modernisation Engine, lock-file lane (uv-lock round). Base: committed HEAD `9788e292128c0742601c125cab09546c2f75570a` (branch `build/phase0`), starting from the controller-verified round-2 state at 187 tests / 0 failed/error/skipped with lint and validator green. Tree left DIRTY with the manifest below; NO commit/push performed (parent commits after verification). NO network, NO uv/resolver execution, NO walkie execution, NO new delegation. All gate runs used the UNCHANGED approved envelope: `python3 -B /home/kensei/projects/modernisation-benchmarks/control/run-development.py <lane>` (pinned rootless image, uid 65534, read-only /source, read-only /benchmark, no network, per-run receipts under `/home/kensei/projects/modernisation-benchmarks/control/evidence/`). `schema_version` stays 2; `tests/unit/test_review_regressions.py` stays byte-unchanged (sha256 `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c` re-verified post-change).

## Controller receipts reconciled (independently verified before this round)

- `development-all-1792364721394260961.json` — 187 passed / 0 failed / 0 errors / 0 skipped (unit+integration; /benchmark byte-identity ran with 0 skips).
- `development-lint-1792364731536094792.json` — ruff pass (exit 0).
- `development-validate-1792364746276505705.json` — plugin validator pass (exit 0).

## This round's fixes (1-9 as briefed), with witnessed RED/GREEN

TDD sequence: ONE witnessed RED run first (all new fail-closed behaviours in the tree with production unchanged), then implementation, then focused GREEN, then full gates.

1. HIGH — ci.yml matrix-fence blind spot (`recipes.py`). The fence returned only a count; the edit was a whole-body `count(find)==1` byte-exact replace, so a drifted suite pin plus a coincidentally-equal other-job pin passed the fence and edited the WRONG job line (native-windows instead of the suite) while reporting success. Now: `_validate_matrix_preimage` returns the exact fenced suite-pin bracket SPAN and `_replacements` applies the single reviewed edit ONLY inside that span (`_apply_anchored_matrix_edit`), additionally refusing if the fenced span drifted or the anchored edit did not yield exactly one target pin. The suite hit is bound to its real reviewed job shape: the enclosing matrix block must pair the pin with the reviewed suite os entries `[ubuntu-latest, macos-latest]` (the reviewed native-windows matrix has no os pair and cannot pass as the suite). Other standalone pins must remain the reviewed single-element `["3.12"]` windows pin; any other pin equal to the upgrade target array (derived from the single reviewed CI edit), or a near-miss longer array sharing the suite pin's opening entries `["3.11","3.12"]`, is refused pre-edit. The pristine case (suite equal + windows `["3.12"]`) keeps applying byte-exactly.
2. MEDIUM — residue fence gap (`recipes.py` result assembly). The result dict and the lock-lane assembly (including the `_lock_delta` build over the pinned bytes) sat OUTSIDE the post-mkdir try/_residue_mark block while the block comment claimed every post-existence failure is marked. The whole result/lane assembly now lives inside the same try fence: any failure after the destination exists writes residue.json and the OSError wrap is unchanged.
3. MEDIUM — truthful adapter description (`adapters/hermes.py`). `DESCRIPTIONS["recipe"]` no longer claims only a per-file unified diff: it declares the reviewed-replay lock lane (owner-reviewed, hash-pinned byte replay) and the real diff surface (text metadata keeps a per-file unified diff; uv.lock carries provenance plus a package-level delta instead of a line-level diff). Plugin manifest text makes no differing claim; registered-tool descriptions render from the same string.
4. MEDIUM — pyproject dev-pin fence exact-state (`recipes.py`). The parsed dev fence was membership-only; a tree with BOTH `pytest-asyncio==0.24.0` and `pytest-asyncio==1.4.0` passed and the replay produced a duplicate 1.4.0 pin. The fence now requires the exact reviewed preimage state (each reviewed preimage pin present exactly once via `dev.count(pin) == 1`; the mirror target pins absent), refusing otherwise before materialisation.
5. MEDIUM — target-valued other pins (edge r3 #4, folded into the same fence as fix 1). A standalone pin equal to the post-edit target array (or the near-miss class) is refused pre-edit, so the replay can no longer produce a duplicate 3.14 matrix entry.
6. LOW — `_lock_delta` truncation marker moved out of band. The bounded-entries `__truncated__` sentinel could collide with a real package name at the 64-entry bound and mask it. Truncated sections are now `{"entries": <64 bounded>, "truncated": true}` plus the pre-existing top-level `truncated` boolean; non-truncated sections keep their plain shape (the reviewed round-2 result shape is unchanged for the real delta, which truncates nothing).
7. LOW — `_artifact_bytes` open now carries `os.O_NONBLOCK` (same pattern as `evidence._read_output` / `identity.read_source`) so an intermediate `data/` symlink pointing at a FIFO cannot hang the open before the existing fstat regular/single-link/size class checks; every existing fstat and pinned-sha fence is unchanged.
8. LOW — walkie lock-row oracle no longer silently no-ops (`test_metadata_recipe.py`). When the mount exists without uv.lock the starlette lock-row oracle previously skipped itself silently. The cross-check now records an explicit `pytest.skip("recorded skip: walkie mount shape lacks uv.lock - starlette lock-row oracle not exercised for the partial mount")`.
9. Docs truth — this handback; TODO/PLAN/HANDOFF current sections updated with round-3 receipts; the wheel-packaging stanza claim is recorded as UNEXERCISED below; the three controller-run receipts above are reconciled into the docs.

## Wheel-packaging claim — UNEXERCISED (recorded)

`next-slice-locklane.md` row "…`[tool.setuptools.package-data] hermes_modernisation = ["data/*"]` so the bundled artifact ships in wheels" is recorded UNEXERCISED: the stanza is standard setuptools configuration, but NO wheel build exists or is planned this round; the exercised distribution path is directory/source installs exercised by the gate receipts. No wheel/sdist evidence exists in the repo or the control tree.

## Receipts for this round (per behaviour RED, then GREEN)

- Witnessed RED (production unchanged, every new fail-closed behaviour failing for its intended defect): `development-unit-1792365794194161529.json` — 173 collected, 9 failed, 164 passed, 0 skipped, exit 1 (designed RED). The nine failures are the nine new behaviours below; failure reasons are in `development-unit-1792365794194161529.log`:
  - fix 1d: `test_lock_lane_refuses_drifted_suite_with_old_suite_pin_on_windows` (drifted suite + old suite array on windows previously applied the TARGET array to the WRONG job and succeeded);
  - fix 1c: `test_lock_lane_refuses_near_miss_extended_suite_pin`;
  - fix 5: `test_lock_lane_refuses_preexisting_upgrade_target_matrix_pin` (previously produced a duplicate-target candidate);
  - fix 6: `test_lock_delta_truncation_marker_is_out_of_band` (real package named `__truncated__` previously masked by the in-band sentinel);
  - fix 6 collision witness: `__truncated__` as a REAL changed package keeps its true `["1.0","2.0"]` delta;
  - fix 2: `test_recipe_residue_records_delta_assembly_failure` (fault-injected `_lock_delta`; previously the materialised candidate root was left WITHOUT residue.json);
  - fix 7: `test_artifact_bundle_fifo_behind_data_symlink_refused_nonblocking` (previously the open blocked on the FIFO — witnessed by the 5 s join probe in the RED receipt);
  - fix 4: `test_dev_pin_preimage_refused_for_both_pin_states_in_dev` (previously a duplicate 1.4.0 candidate was produced);
  - fix 3: `test_recipe_adapter_description_declares_replay_lane_and_diff_surface`;
  - fix 8: `test_walkie_lock_oracle_records_explicit_skip_for_partial_mount` (previously the partial-mount oracle silently no-oped: `DID NOT RAISE Skipped`).
- Focused GREEN (unit lane after implementation): `development-unit-1792365944748977299.json` — 173 passed / 0 failed / 0 errors / 0 skipped, exit 0 (byte-identity oracle ran against /benchmark with 0 skips).
- Full `all` gate: `development-all-1792366054774577730.json` — 197 passed / 0 failed / 0 errors / 0 skipped, exit 0.
- Lint: `development-lint-1792366056200655162.json` — ruff "All checks passed!", exit 0.
- Plugin validator: `development-validate-1792366064084112672.json` — `ok: true` on every checked surface, `warnings: []`, exit 0.
- Characterisation guard (passes at RED and GREEN by design, protecting the reviewed shape): `test_real_reviewed_shape_still_applies_with_windows_pin_carveout` — real baseline bytes apply with the anchored edit, windows `["3.12"]` pin untouched.

## Changed-file manifest (round 3 delta only; tree left dirty)

- `src/hermes_modernisation/recipes.py` — fence constants (`_DEV_PINS_TARGET`, `_MATRIX_SUITE_OS`, `_MATRIX_WINDOW_PIN`), exact-state dev-pin fence, anchored matrix fence returning the suite span + `_workflow_list`/`_matrix_target_pins`/`_enclosing_matrix`/`_matrix_block`/`_apply_anchored_matrix_edit` helpers, `_validate_parsed_preimage` span contract, `_replacements` anchored path, out-of-band `_lock_delta` truncation shape, `_artifact_bytes` `O_NONBLOCK`, result/lock-lane assembly moved inside the residue fence.
- `src/hermes_modernisation/adapters/hermes.py` — `DESCRIPTIONS["recipe"]` truthfulness.
- `tests/unit/test_metadata_recipe.py` — `FIXTURE_CI` reviewed matrix shape, `BENCHMARK` constant extraction (neutral), explicit partial-mount skip guard in the walkie cross-check, three new tests.
- `tests/unit/test_lock_recipe.py` — six new tests plus the characterisation guard.
- `docs/evidence/next-slice-interim4.md` (checkpoint), `docs/evidence/next-slice-locklane-round2.md` (this handback), `docs/evidence/next-slice-locklane.md` (UNEXERCISED annotation on the wheel row), `docs/TODO.md`, `docs/PLAN.md`, `docs/HANDOFF.md` (round-3 receipt/manifest reconciliation).

## Honest boundary

The lane still REPLAYS one owner-reviewed, already-tested resolution result and resolves nothing new; genuinely new dependency resolutions remain a separately scoped, signature-gated lane. The matrix fence refuses exactly the briefed classes (target-equal and suite-adjacent near-miss other pins, unbound suite hits); a standalone pin outside the reviewed shape that is neither (e.g. some future single-element pin other than `["3.12"]`) still passes the fence unchanged from round 2 — noted as the deliberate boundary of this round's mandate. Independent capture, authenticated receipts and stored candidate-staging binding remain open. Prior real-run grants remain consumed/stale.
# Interim checkpoint 4 — uv-lock lane correction round 3 (in progress)

Date: 2026-10-19 (BST). Branch `build/phase0`, committed HEAD `9788e292128c0742601c125cab09546c2f75570a`, tree DIRTY (round-2 delta + this round's edits). NO commit/push. Gate envelope UNCHANGED: `python3 -B /home/kensei/projects/modernisation-benchmarks/control/run-development.py {unit,all,lint,validate}` (pinned rootless image, /source read-only, /benchmark read-only, no network, per-run receipts under `/home/kensei/projects/modernisation-benchmarks/control/evidence/`).

## Controller-verified starting receipts

- `development-all-1792364721394260961.json` — 187 tests, 0 failures/errors/skips.
- `development-lint-1792364731536094792.json` — lint pass.
- `development-validate-1792364746276505705.json` — plugin validator pass.

These three controller-run receipts are the baseline this round starts from (reconciled in the round handback, not re-claimed by this lane).

## Round-3 scope (nine bounded fixes from the Hermaguard r3 reports)

Edge (`deleg_5a8b1a58/task-0.log`), adversarial (`task-1.log`), blast (`task-2.log`). Fixes 1-9 per the controller brief: (1) HIGH ci.yml matrix fence blind spot — span-anchored edit + suite-job os binding + other-pin refusal classes + RED drift witness; (2) MEDIUM residue/assembly gap — result and lock-lane assembly moved inside the fence; (3) truthful adapter `DESCRIPTIONS["recipe"]`; (4) exact-state dev-pin fence (each preimage pin exactly once, target pins absent); (5) refuse pre-existing target-valued other pins; (6) out-of-band truncation marker in `_lock_delta`; (7) `O_NONBLOCK` on the artifact open; (8) explicit recorded skip for the partial-walkie-mount lock-row oracle; (9) docs truth including the wheel-packaging claim marked UNEXERCISED.

## State at this checkpoint (all receipts below are from THIS round unless noted)

- Test layer DONE (production untouched so far):
  - `tests/unit/test_metadata_recipe.py`: `FIXTURE_CI` now mirrors the reviewed workflow matrix shape (suite `os: [ubuntu-latest, macos-latest]` paired with the python-version pin); `BENCHMARK` module constant extracted (neutral refactor; walkie test reads it); new RED tests `test_dev_pin_preimage_refused_for_both_pin_states_in_dev`, `test_recipe_adapter_description_declares_replay_lane_and_diff_surface`, `test_walkie_lock_oracle_records_explicit_skip_for_partial_mount` (expects `pytest.skip` for a partial mount — currently the cross-check's lock-row oracle silently no-ops).
  - `tests/unit/test_lock_recipe.py`: new RED tests — `test_lock_lane_refuses_drifted_suite_with_old_suite_pin_on_windows` (fix 1d, wrong-job edit currently SUCCEEDS), `test_lock_lane_refuses_near_miss_extended_suite_pin`, `test_lock_lane_refuses_preexisting_upgrade_target_matrix_pin` (fix 5, currently produce a duplicate-target candidate), `test_lock_delta_truncation_marker_is_out_of_band` (fix 6, current in-band `__truncated__` sentinel would mask a real package named exactly that), `test_recipe_residue_records_delta_assembly_failure` (fix 2, fault-injected `_lock_delta`; residue currently missing on assembly failure), `test_artifact_bundle_fifo_behind_data_symlink_refused_nonblocking` (fix 7, current open would hang on a FIFO behind an intermediate `data/` symlink), plus characterisation `test_real_reviewed_shape_still_applies_with_windows_pin_carveout` (regression guard for the reviewed `[\"3.12\"]` windows carve-out over the REAL baseline bytes).
- Production fixes 1-9: NOT YET applied. Next action: witnessed RED receipt via the approved gate `unit` lane, then implement, then focused GREEN + full `all`/`lint`/`validate`.
- Out of scope unchanged: no wheel build, no new resolution lanes, no evidence/store/runner edits, `schema_version` stays 2, `tests/unit/test_review_regressions.py` untouched (frozen sha256 `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c` verified at slice start).

## Budget/notes

Tool budget on plan: ~80 calls. Interim written before the RED gate run. No unbacked counts are stated above: current-suite counts beyond the controller receipts are intentionally omitted until the RED/GREEN receipts name them.

## Close-out (final of this round)

Implementations of fixes 1-9 landed after the witnessed RED, with one intermediate defect caught by the gate itself (initial fence used the wrong capture group after the two-group regex change; corrected and evidenced):

- RED: `development-unit-1792365794194161529.json` — 173 collected, 9 failed, 164 passed, 0 skipped, exit 1 (designed RED; failure reasons per behaviour in the paired `.log`).
- Intermediate (wrong capture group, 13 failed — existing FIXTURE_CI tests refused wrongly): `development-unit-1792365888500205889.json`, corrected next receipt.
- Post-group-correct, focused run: 1 failure (`development-unit-1792365917419095928.json` — delta-truncation test data corrected: the real `__truncated__` package's true changed pair, not a scalar, is the mask witness).
- Focused GREEN: `development-unit-1792365944748977299.json` — 173 passed, 0 failed/error/skipped.
- Full `all`: `development-all-1792366054774577730.json` — 197 passed, 0 failed/error/skipped; lint: `development-lint-1792366056200655162.json` (pass); validator: `development-validate-1792366064084112672.json` (ok, warnings empty).
- Round handback with the changed-file manifest + controller-receipt reconciliation: `docs/evidence/next-slice-locklane-round2.md`.
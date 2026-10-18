# Controller verification — uv-lock lane round 3 (fix round)

Date: 2026-10-19 00:40–00:55 BST. Tree: build/phase0 @ `9788e292128c0742601c125cab09546c2f75570a` + dirty lock-lane delta + round-3 fixes (uncommitted; committed after this record following final review).

## Controller-run evidence (all receipts under `/home/kensei/projects/modernisation-benchmarks/control/evidence/`)

- Full gate **all**: **197 passed, 0 failed, 0 errors, 0 skipped**, exit 0, 51.6 s, byte-identity oracle ran (0 skips) — my receipt `development-all-1792366302941641512.json`. Matches implementer.
- Lint pass — `development-lint-1792366309142910880.json`. Plugin validator ok:true 14/14 — `development-validate-1792366318352311998.json`.
- Implementer receipts parsed and confirmed: RED 173/9 (`development-unit-1792365794194161529.json`), focused GREEN 173/0 (`development-unit-1792365944748977299.json`), plus the two transient intermediate receipts (`1792365888500205889` 173/13 and `1792365917419095928` 173/1) matching the self-caught regex capture-group defect the gate itself caught and fixed mid-round.
- `tests/unit/test_review_regressions.py` byte-unchanged (sha256 `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c`); whitespace clean.

## Source spot-checks (read, not inferred)

- Matrix fence/edit: `_apply_anchored_matrix_edit` (recipes.py:273+) replaces exactly inside the fence-asserted span, never by whole-body search; suite hit bound to the reviewed job shape (os pairing); other standalone pins restricted to the reviewed windows carve-out; target-equal / near-miss pins refused pre-edit; target array derived from the single reviewed CI edit.
- Artifact loader now uses `O_RDONLY|O_NOFOLLOW|O_NONBLOCK` with unchanged fstat/size/pinned-sha fences (recipes.py:389-401).
- `_lock_delta` truncation moved out of band (`{"entries": …, "truncated": bool}`), in-band `__truncated__` sentinel gone (recipes.py:510-519).
- Residue fence widened to cover result/lock-lane assembly; `DESCRIPTIONS["recipe"]` (adapters/hermes.py:94-97) now truthful: metadata replay, per-file diff for text metadata only, provenance + package-level delta for the lock.
- Docs truth updates bounded to current-position sections with receipts; wheel-claim marked UNEXERCISED; schema stays 2; evidence/store/runner/proposals untouched.

## Verdict

Round-3 fix lane ACCEPTED on controller receipts. The Hermaguard r3 findings are closed: HIGH (wrong-job-edit blind spot), both MEDIUMs (residue/assembly window, stale tool description), and the LOWs (dev-pin and matrix fence tightenings, sentinel collision, artifact O_NONBLOCK, silent oracle no-op) plus docs-truth reconciliation. Deferred by design (unchanged): wheel-build evidence (no wheel exists in this lane), permanent rejections (backup auto-deletion, speculative limits, transport renames), deferred LOW engineering items (/proc magic-link probe, producer argv abbreviations, output-cap composition, A-5 seam, A-6 divergence, producer marker-scan).

Open lane limits (honest): replay ≠ new resolution; NOT_PROVEN grading; caller-declared candidate digest; native run/resume/approve still refuse; no install/merge/public changes. This is a private-repo code acceptance only — no release decision.

## Next

Trial lane preparation (owner signatures for any real-project run) starts after this tree is committed: fresh requests bound to the then-current engine identity; old grants never replayed; ONE signing command for the owner; execution only on fresh signatures.
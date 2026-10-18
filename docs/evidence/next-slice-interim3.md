# Interim checkpoint 3 — uv.lock replay lane (in progress)

Date: 2026-10-19 (BST). Branch `build/phase0`, HEAD `9788e292128c0742601c125cab09546c2f75570a` (clean at start of slice). Tree now dirty with this slice only. NO commit/push made.

## What this slice is

The lock lane: engine ingests the owner-reviewed, already-tested v4 upgraded `uv.lock` bytes as a hash-bound, provenance-carrying DATA artifact (committed under engine-owned sources), extends the fixed recipe with a byte-exact uv.lock replay gated by a DIGEST preimage, and proves completion by byte-identity against the real v4 candidate. No resolution, no network, no uv, no resolver execution.

## Verified input facts (captured read-only from the benchmark clone; never modified)

- Baseline: walkie `bdbc72300bb494a393992bf4b49259c06811c2b9` (original repo baseline per docs/HANDOFF.md §5). `git show bdbc723:uv.lock` sha256 = `a28285e4787ac1a478a3fc1942b55b4c631678c201566276a3b73d23154b2396` — matches the owner-recorded baseline lock digest.
- v4 follow-up commit `c6134c20f66122347f61b93fa133cf47521d6700` ("test(deps): pytest-asyncio 1.4.0, starlette 0.52.1 lock") on top of candidate `cc191ca18e7529097c2cb3095ca8b803957f5598`. Its uv.lock = `a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25` (116,343 bytes). Clone working tree verified byte-identical to that blob (clean status).
- Package-level delta captured from real bytes: fastapi 0.115.6→0.133.1, httpx 0.27.2→0.28.1, pytest-asyncio 0.24.0→1.4.0, starlette 0.41.3→0.52.1; added `annotated-doc 0.0.5`; removed `sniffio 1.3.1`.
- pyproject baseline→candidate has NO starlette pin; the only v4 pyproject change is the dev pin pytest-asyncio 0.24.0→1.4.0.

## Committed data bundle (new files, tree dirty)

- `src/hermes_modernisation/data/uv.lock.v4-replay` — artifact bytes, sha256 `a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25`.
- `tests/unit/data/baseline/uv.lock`, `tests/unit/data/baseline/pyproject.toml` (`427173b5c439c94a62e25c32b7b2365f831e2637d74fbd5e1a251f9da6bb50ce`), `tests/unit/data/baseline/.github-workflows-ci.yml` (`ebf3db4baea312a8bf98deea203c6520ba5f242e78948f8a62f3be8b24f2c7fb`) — pristine baseline bytes for fixtures.

## RED witnessed (gate: approved isolated dev container; receipts exact)

`development-unit-1792364322089255491.json` (+ `.log`): unit lane 163 collected, **9 failed**, 154 passed, 0 error/skipped. Failure reasons verified behavioural:

1. `test_lock_lane_replays_reviewed_artifact_byte_exact` — changed_paths lacks uv.lock (lane absent).
2-5. drifted-lock / absent-lock / completed-already / artifact-tamper: DID NOT RAISE (all four fail-closed fences missing).
6. `test_dev_pin_bump_joins_parsed_fields` — 1.4.0 absent, 0.24.0 retained.
7-8. dev-pin absent/preimage and comment-token analogies: DID NOT RAISE.
9. `test_byte_identity_with_real_v4_candidate` — **unexpected-but-real defect exposed**: the reviewed single-python-version-line CI preimage refuses the REAL baseline workflow (two bracketed matrix pins: 3.11-3.13 suite + windows `["3.12"]`). The recipe therefore never could apply to the real baseline tree; the CI preimage must match the real reviewed shape without weakening (fix planned, in-scope for proof (c)).

Non-RED by design (documented): `test_recipe_refuses_symlinked_lock` passes pre-GREEN via the shared snapshot/read_source no-follow fences; it is kept as regression coverage for the lock path, not claimed as a distinct defect witness.

## Remaining in this slice (ordered)

1. Implement the lock lane: digest preimage (drift/absent/completed-already refused), artifact self-tamper check before materialisation, byte-exact replacement, package-level delta summary in the result (line-level lock diff deliberately omitted per design (d)), declared replay label (honest "REPLAYS reviewed v4 result; does NOT resolve" (e)), dev-pin edit + parsed preimage.
2. Fix the CI matrix preimage to the real baseline shape (exactly one 3.11-3.13 pin line; additional distinct bracketed pins such as the windows `["3.12"]` job pin remain untouched by the recipe).
3. Update `tests/unit/test_metadata_recipe.py` expectations for the extended lane (changed_paths incl. uv.lock; updated declared-refusal entries), leaving no weakened assertions.
4. GREEN focused, then full `all` + `lint` + `validate` receipts. Keep 177 pre-existing tests green; `test_review_regressions.py` unmodified (sha `d3823e2b18a92d934bfc0fbbb36e343e7a537becd2f9e4f843c72dd99c551c6c` verified).
5. Byte-identity proof (c) against `/benchmark` (0 remaining declared differences), docs current-position updates (TODO/PLAN/HANDOFF receipt-backed), handback `docs/evidence/next-slice-locklane.md`, manifest of changed files, tree left dirty, NO commit/push.
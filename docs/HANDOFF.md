# Resume here — Modernisation Engine

## ACTIVE BUILD — configured protected checking works on owned fixtures; points 2–3 still open

Current source-bound checkpoint: `docs/evidence/remaining-build-20261020/build-recovery.json` (270 tests, zero failures/errors/skips; lint and warning-free validator green). The earlier configured-capture checkpoint is preserved. Actual runtime recovery now covers five process-loss checkpoints and cooperative cancellation, with live-worker locking, exact signed retirement, cleanup readback and no partial-evidence adoption/replay. The configured public Engine now performs assess/contract/signed review/baseline/proposal/migration review/engine-owned build/candidate/compare/report. A real rootless owned-fixture journey passed 15 protected responses per phase; original unchanged, both containers removed/read back, compare/report launched nothing. No expected values enter candidate mounts. Stored observations are re-derived against private artifacts, exact consumed authority and engine/source/contract bindings; imported JUnit remains reported-only. Native CLI/tool/registered-slash review acceptance/forgery/replay controls and shared standalone CLI parsing are exercised.

Build-reservation recovery additionally passed three actual pre/during/post-copy controller-loss cases, preserving failed paths, requiring a fresh signed migration review and rebuilding into new namespaces.

Do NOT mark the parent points complete: the complete schema/state/profile/concurrency matrix, full native/gateway execution journey, complete strict schemas, broader adapters/resolution, offline model/budget/batch work, rule adequacy and signed narrow differences remain open. Completed-only resume revalidates; uncertain attempts refuse replay. Fixture keys are not Sahil approval. Live execution remains unconfigured, no live install/settings/credential/provider changes occurred, and point 4 stays HOLD. Continue from `docs/plans/2026-10-20-remaining-build.md`; preserve all original M0–M8/MT01–18 requirements.

The section below records the earlier docs-only checkpoint; the current feature delta is now executable and separately verified. Historical v5 commands/signatures remain spent.

## CURRENT — 20 October 2026: real trial complete; points 1–3 BUILD authorised

Read [NEXT-SESSION.md](NEXT-SESSION.md) and [the v5 checkpoint](evidence/trial-v5-20261019/README.md) FIRST. The previous paused trial DID run successfully, baseline first then upgraded candidate: the same twenty checks passed with zero failures/errors/skips/warnings. Evidence is still candidate-authored, outer verdict NOT_PROVEN. Both one-use permissions are consumed; no more signing/replay is required for ordinary engineering.

Latest producing executable baseline: `c343e0bbb26f613571dd03602321b74b08b4ecf2`. Its full engine gate was 197 passed, zero failures/errors/skips, lint and validator green. The older `b914c6d` and signature-pending/current-position notes below are HISTORICAL, superseded here. For this checkpoint the delta from c343 is docs/recovery only. Subsequent feature work must record and test its actual production delta.

The owner now authorises DIRECT isolated work through points 1–3: save this checkpoint, complete protected independent checking and prerequisite contract/state/authority work, then finish the bounded full workflow. Test each change. STOP before point 4's separate final independent audit/release decisions. No new paid/model egress, live installation/config/restart, public writes, destructive cleanup or implicit real-project execution approval.

Current trial summary/provenance: `docs/evidence/trial-v5-20261019/`. Historical v5 controller sources/probes: `development/recovery/owner-v5/` (immutable as-used layout, NOT runtime commands). Real signatures, live request packages, databases and private keys remain local and outside Git. Never replay/reset them or run the archives blindly.

The dated handoff below preserves prior history and reproducibility limits. Its old pending-request paths are NOT current instructions.

## 1. State and read order

The work is deliberately parked as a **PARTIAL engineering preview**, not a finished engine. This handoff requires no chat history. Read:

1. [TODO.md](TODO.md): completed subcomponents checked off, full remaining register and immediate order.
2. [PLAN.md](PLAN.md): updated current position plus original design preserved verbatim.
3. [compatibility.md](compatibility.md), [threat-model.md](threat-model.md), [provenance.md](provenance.md).
4. [evidence/checkpoint-2026-10-15.json](evidence/checkpoint-2026-10-15.json): immutable summary of producing identities, test scopes and payload hashes.
5. [development-checkpoint.md](development-checkpoint.md): historical producing-session detail, NOT a fresh state query.

Private remote intended for this checkpoint: `Sahil-SS9/hermes-modernisation-engine`. Branch retained: `build/phase0`. Baseline implementation: `b914c6d118584a45736611c93bb772905108acd6`. The handoff/push commits are additive docs/recovery files; verify the delta rather than pinning a self-changing final HEAD. README links are navigation updates, not changed execution semantics.

## 2. Locked boundaries

- DIRECT implementation only. No workers, delegation or agent CLIs. Do not reinterpret the unrelated Skill Foundry pin as an engine dependency.
- User authorised private GitHub checkpoint backup. No public repo/release, no live install/config/restart, no original walkie-talkie write/push, no deployment or destructive cleanup.
- Real source code executes only in the approved disposable rootless sandbox with exact authentic owner grants. Current native run/resume remain disabled.
- Compare/report/status never launch fresh old/new programs or models. Imported/caller-authored data is not authenticated proof.
- No new model egress, paid experiments or owner-private-key access. Do not read, upload, regenerate or search for the real owner's private key. Preserve old consumed grants only in protected local storage; never replay them.
- Keep complete failed/superseded evidence. A docs checklist is not independent implementation approval.

## 3. Verify first — read-only checks

From the existing local checkout:

    git status --short --branch
    git rev-parse HEAD
    git merge-base --is-ancestor b914c6d118584a45736611c93bb772905108acd6 HEAD
    git diff --name-only b914c6d118584a45736611c93bb772905108acd6..HEAD
    git remote -v
    gh repo view Sahil-SS9/hermes-modernisation-engine --json isPrivate,url,defaultBranchRef

Expected: clean tree, branch `build/phase0`, descendant of the implementation baseline; checkpoint delta only README/.gitignore/docs/development recovery content; authenticated repository visibility private. Any unexpected executable production change requires new scoped verification. Do not reset unrelated work.

Verify recovery bytes:

    cd development/recovery
    sha256sum -c SHA256SUMS

The recovery scripts are ARCHIVAL copies of trusted local control recipes, not portable executables from their new location. Some intentionally retain original paths or calculate `ROOT` from `__file__`; restore/review their documented layout before running. Never run an archived script blindly from `development/recovery`.

## 4. Existing-machine reproduction

Existing local control root: `/home/kensei/projects/modernisation-benchmarks/control`.
Engine root: `/home/kensei/repos/hermes-modernisation-engine`.
Rootless development image: `modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6`.

Read-only runtime preflight:

    docker info --format '{{json .SecurityOptions}}'
    docker image inspect modernise-validator-fixed:local --format '{{.Id}}'

Expected rootless security option and exact pinned image ID. If prerequisites are missing, record BLOCKED; do not use the live host or install dependencies globally.

Full preview gate (actually executed successfully on this machine):

    python3 -B /home/kensei/projects/modernisation-benchmarks/control/run-development.py checks

Expected at the code baseline: 108 tests passed, zero failures/errors/skips, lint pass and native validator `ok: true`; private JSON/log receipt path printed; no remaining test container. The source tree remains read-only and unchanged. This script invokes the committed `scripts/checks.sh` inside the verified container, NOT host pytest. After the 18 October 2026 slices (public evidence workflow, protocol producer, fixed-recipe metadata lane) plus correction round 2: full `all` gate 177 passed / 0 failed/error/skipped (`development-all-1792362828928180702.json`), unit lane 153 passed (`development-unit-1792362777197147952.json`), lint pass and plugin validator ok:true (`development-lint-1792362832466850699.json`, `development-validate-1792362838314682993.json`); RED witnesses are `development-unit-1792362347013821392.json` (144 collected, 4 failed — controller regressions) and `development-unit-1792362701142033942.json` (153 collected, 13 failed — each correction behaviour). A round-2 claim of a green 168-test gate was retracted as unsupported; see `docs/evidence/controller-review-correction.md`. After the 19 October 2026 uv.lock replay lane (committed base `9788e292128c0742601c125cab09546c2f75570a`): RED `development-unit-1792364322089255491.json` (163 collected, 9 failed — all new fail-closed behaviours plus the real-tree CI-preimage defect), focused GREEN `development-unit-1792364475213004576.json` (163 passed, includes the /benchmark byte-identity proof with 0 skips), full `all` `development-all-1792364519172862306.json` (187 passed, 0 failed/error/skipped), lint `development-lint-1792364523114204273.json` (pass), validator `development-validate-1792364528964942372.json` (ok:true, warnings empty). See `docs/evidence/next-slice-locklane.md` for the handback and manifest. Correction round 3 (19 October 2026) on the same base: RED `development-unit-1792365794194161529.json` (173 collected, 9 failed — all nine new fail-closed behaviours: span-anchored matrix fence with suite-job os binding, residue-covered assembly, truthful recipe description, exact-state dev-pin fence, out-of-band delta truncation marker, non-blocking artifact open, partial-mount recorded skip; the drifted-suite/wrong-job-edit and duplicate-target candidates previously succeeded), focused GREEN `development-unit-1792365944748977299.json` (173 passed, 0 failed/error/skipped), full `all` `development-all-1792366054774577730.json` (197 passed, 0 failed/error/skipped), lint `development-lint-1792366056200655162.json` (pass), validator `development-validate-1792366064084112672.json` (ok, warnings empty); the controller-run receipts `development-all-1792364721394260961.json` (187/0), `development-lint-1792364731536094792.json` and `development-validate-1792364746276505705.json` are reconciled; handback + manifest in `docs/evidence/next-slice-locklane-round2.md`; the wheel-packaging stanza claim is UNEXERCISED (no wheel build exists or is planned — directory/source installs are the exercised path).

Separate canonical host subset (not an extra 34 distinct engine tests):

    python3 -B /home/kensei/projects/modernisation-benchmarks/control/canonical-disposable.py

Expected 34 selected validator tests, zero failed, exit 0, timing cache saved inside disposable `/work`. Known warning: Git absent at bytecode-preparation step; test runner still exits 0. Do not claim a warning-free/full-host run. Avoid needless repeat runs when identities and evidence are unchanged.

## 5. Benchmarks, host patch and authority

Original repository: `/home/kensei/repos/hermes-walkie-talkie`, clean `main`, baseline `bdbc72300bb494a393992bf4b49259c06811c2b9`. Isolated clone: `/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie`, `test/modernisation-fastapi`, candidate `cc191ca18e7529097c2cb3095ca8b803957f5598`, no remote. Only pyproject/lock/CI metadata changed.

Lock-replay provenance (19 October 2026): the engine bundles the v4 candidate lock bytes captured READ-ONLY from this clone at commit `c6134c20f66122347f61b93fa133cf47521d6700` (the pytest-asyncio 1.4.0 / starlette 0.52.1 follow-up on top of the candidate); the clone's working tree was verified byte-equal to that commit and the clone was NOT modified. Baseline lock digest (at `bdbc723`): `a28285e4787ac1a478a3fc1942b55b4c631678c201566276a3b73d23154b2396`; replayed artifact digest: `a12493e00ea9c28d204dadbe52a3edd6a63f14b23f390a361591dfebafe49b25`. The recipe pins both digests and refuses drift/re-resolution; the lane REPLAYS the owner-reviewed v4 result and resolves nothing.

Update 17 October 2026: bounded candidate behavioural runs DID take place under fresh owner-signed one-use v3/v4 grants (order enforced, replay refused). The selected upgrade passed its declared 20-test API/auth scope with identical per-case outcomes; per-case evidence remains candidate-authored JUnit (NOT_PROVEN). See `RESULT-v3-20261017.txt`, `RESULT-v4-20261017.txt` and the TODO/PLAN current sections. Update 18 October 2026: the engine core identity changed again (public evidence workflow + fixed-recipe lanes), so every previous request/grant is stale or consumed — never replay an old signature; any future real run needs a freshly prepared grant bound to the then-current engine identity.

The exact candidate diff is backed up at `development/recovery/benchmark-candidate.patch`. It is NOT permission to apply to the original or public repo. For a lost machine, recreate a separate clone at the pinned base and apply/review the patch there. Confirm original tests and source logic remain byte-identical. Recreating the original commit object may require fetching it from public history; do not invent a new base when unavailable.

Pinned native host PR: `NousResearch/hermes-agent#138686`, head `4539b09a730d6a97548b4d4102d10990033ead36`. Do not assume it is still open/unmerged or compatible at pickup: query GitHub and revalidate. The separate validator repair is in `development/recovery/validator-fix/validator-handles.patch`; it must not be silently applied to live Hermes or mistaken for part of the unmodified PR. Host Dockerfiles are archival preparation recipes; rebuild only after verifying their source pins/contexts and permitted network/dependency scope. No host source tree, external reference source or Docker image binary is stored in this repo.

Fresh owner request directory at checkpoint:
`/home/kensei/handoff/agent-plugin-plans/approvals/walkie-v2-1792072605580412472/`.

Expiry: Unix 1792245405, 17 October 2026 14:56:45 BST. At any later pickup, check the real clock; regenerate exact requests and obtain new authentic signatures if expired or any bound identity changed. Old consumed baseline approval is historical only. The signing question was skipped; no signature received for these new requests at checkpoint.

Inert request preflights, executed successfully at checkpoint:

    /home/kensei/projects/modernisation-benchmarks/control/operator-env/bin/python -B /home/kensei/projects/modernisation-benchmarks/control/run-owner-v2.py baseline --preflight
    /home/kensei/projects/modernisation-benchmarks/control/operator-env/bin/python -B /home/kensei/projects/modernisation-benchmarks/control/run-owner-v2.py candidate --preflight

Expected `execution_performed:false`, `authority_claimed:false`. These paths remain LOCAL ONLY, intentionally not uploaded because they are tightly bound to owner authority metadata. If lost, re-establish external owner enrolment and request generation explicitly; never substitute fixture keys for the owner.

Important correction: signatures unblock only the bounded real regression lane. Strict contracts, state/fencing and fixture safety coding can continue independently, subject to build authority; the entire backlog is not blocked by signing.

## 6. Clean-machine recovery limitations

The private GitHub repository backs up consumer source/tests/lock, the full updated/original design, known recovery recipes, the host patch and benchmark diff, and sanitised evidence summaries. It does NOT contain working images, full third-party host/reference repos, raw owner/private benchmark data, job DBs, signatures or private keys. Archived public verification keys/fingerprints are not signing authority. Expect explicit prerequisite reconstruction on another machine, not a one-command full reproduction promise.

Development fixture/reference tests require `/source`, `/reference` and `/benchmark` read-only mounts. Do not advertise `uv run pytest` on a bare clone as the full host/isolation gate. Reference pin and download hashes are in provenance and the checkpoint. Synthetic executor fixtures also expect empty `empty/` subdirectories: Git does not store empty directories; create those only inside the disposable fixture setup before rerunning controls, and then regenerate fixture-only approvals.

The user may inspect the private HTML preview locally via the artifact manifest path under `/home/kensei/handoff/agent-plugin-plans/artifacts/`; the remote does not claim to contain those binaries. Rebuild updated artifacts after future code changes and keep old hashes historical.

## 7. Work order when resumed

1. Reconcile current remote/local state and prerequisites; read the checked TODO register. No silent assumption that parked grants or host commits remain valid.
2. Complete M0 prerequisite acceptance and M1 strict full contracts, then M2 attempt/fencing/recovery. Existing preview components are useful foundations, not closed parent phases.
3. In parallel in conceptual planning only (no delegation), owner can approve the exact bounded original/candidate regression lane. Signature does not approve arbitrary commands or model egress.
4. Finish evaluator-owned oracle/receipt acceptance and mutation/normalisation proof, then optional bounded model/batch work and full authorised native journey.
5. Full platform/upgrade/research/value/independent review and separate release decisions. Tick TODO entries only when their exact acceptance evidence exists.

At each pause update TODO/PLAN current-position section, append evidence with producing SHA and boundary, commit only approved scope, and keep private push separate from deployment/public release. Preserve the original plan body for traceability.

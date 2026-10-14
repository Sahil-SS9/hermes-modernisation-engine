# Modernisation Engine — Phase 0 checkpoint

Status: PARTIAL. Sandbox policy and external signature-verification primitives implemented and exercised; the full plugin is NOT built, installed or approved for release.

## Boundary and authority

Sahil approved controller-direct implementation, the separate walkie-talkie clone/test branch, and a sandbox-only external trusted executor direction. No delegation is permitted. No live repo writes, live installation/configuration/credentials/privilege changes, public pushes, merges or deployment are approved.

Engine: `/home/kensei/repos/hermes-modernisation-engine`, local branch `build/phase0`, no remotes, default pushes disabled.
Benchmark: `/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie`, `test/modernisation-fastapi`, base `bdbc72300bb494a393992bf4b49259c06811c2b9`, no remotes, default pushes disabled.
Original: `/home/kensei/repos/hermes-walkie-talkie`, unchanged on main. It is NEVER mounted into the sandbox.
Controlling specification: `/home/kensei/handoff/agent-plugin-plans/.hermes/plans/2026-10-14-modernisation-engine.md` (left unchanged).

## Implemented, not merely proposed

- `src/hermes_modernisation/sandbox.py`: fixed immutable-image Docker argv policy; network none, read-only root/source, no recursively mounted submounts, dropped capabilities, no-new-privileges, uid 65534, 64 processes, 512 MiB memory/no extra swap, one CPU, finite tmpfs/file/open-file limits. No credential directories, broad home mount, socket, device, arbitrary env or privileged option. Pure policy construction is not execution authority.
- `src/hermes_modernisation/approvals.py`: external Ed25519 public-key verification; exact signed operation binding (source/candidate/oracle/environment/image, argv, job/attempt/profile/actor, roots/network/time/output); owner-only durable SQLite one-use claims; replay survives restart; concurrent claims have one winner. Rejected grants do not create the ledger. Caller cannot pass a grant clock. No sign/approve endpoint and no private signing key in the implementation.
- `scripts/sandbox_checks.py`: actual operator-only contained execution using the production launch policy. Fixed engine/lint/walkie-api scenarios only, rootless preflight, 120-second operator ceiling, 4 MiB output cap, container kill on limit, cleanup readback, before/after bounded source-byte digests, private external output/JSON records. It is NOT a general authenticated plugin job endpoint or an equivalence proof collector.
- `tests/unit/test_sandbox_policy.py`, `tests/unit/test_authority.py`, `tests/platform/test_native_isolation.py`: real sandbox tests, including escaped writes, symlinks/hardlinks, external network, absent host paths/sockets/credential env, child containment, kernel seccomp/capability/cgroup controls, signature forgery, expiry, field tampering, unknown keys, replay, concurrent claims and unsafe ledgers.

## Actual execution and evidence

The initial Bubblewrap probe failed (`Failed RTM_NEWADDR: Operation not permitted`); no privilege or isolation flag was weakened. Rootless Docker is the selected development isolation backend. Native tests actually passed under Docker's enforced controls on this Linux host. This is tested containment within the stated profile, not a universal security proof or a VM boundary.

Pinned base image: `python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258`.
Prepared development image: `modernise-sandbox-dev@sha256:49808cb0b9909505e906fcef5e0ea373566c96a0508cbc3f60c2fc38de08217f`.
The image was built with package-registry network access and no user repo mounted. Runtime tests have network NONE. Python/dependencies were installed only INSIDE this image, not into a host/live venv. The image embeds `/dependency-manifest.txt`; direct dependency pins are in `sandbox-image/Dockerfile`. Transitive packages are bound by the actual image digest; a fully hashed rebuild lock is still outstanding.

Witnessed RED: the initial sandbox policy denied all seven intended operations; after implementation the same seven tests passed. The external-authority file initially refused valid signed operations (nine collected, six passing denial controls and three expected valid-operation errors); after implementation the original assertions passed. Later native/concurrency/hardening tests are additional validation, not separately witnessed RED cycles. No import/setup failure is called valid RED.

Latest full owned suite: 29 collected, 29 passed, zero failures/skips, under Python 3.12.15 and pytest 8.4.2 in the contained image. Lint inspected ALL current src/tests/scripts, not a narrowed subset; passed. First lint invocation was blocked by attempted cache creation on the read-only mount; the invocation was corrected to `--no-cache`, not the source mount made writable.

Walkie-talkie baseline slice: 20 collected, 20 passed, zero failures/skips; one upstream Starlette/AnyIO deprecation warning retained. This tests the existing FastAPI 0.115.6 API/WebSocket-auth slice in the prepared development image. It is NOT a lock-faithful original-host baseline, native Hermes dashboard proof, a migrated candidate or the whole walkie-talkie suite. The clone dependency pin/lock/source files have NOT been changed.

Exact commands, process exits, complete output hashes, durations and container cleanup readback are private at `/home/kensei/projects/modernisation-benchmarks/control/evidence/`. Early receipts predate the source-identity fields; only fresh receipts carrying `source_digest_before`, `source_digest_after` and `source_unchanged` bind the final candidate's development run. Records are operator development evidence, NOT counterfeit owner-signed plugin execution receipts. The original `docs/phase0-evidence.json` is historical discovery evidence and remains immutable.

Reproduce the contained development checks:

    python3 -B /home/kensei/repos/hermes-modernisation-engine/scripts/sandbox_checks.py engine
    python3 -B /home/kensei/repos/hermes-modernisation-engine/scripts/sandbox_checks.py lint
    python3 -B /home/kensei/repos/hermes-modernisation-engine/scripts/sandbox_checks.py walkie-api

Only the trusted operator wrapper runs on the host. All project tests and lint run inside containers. No baseline or migration program runs unsandboxed.

## Remaining Phase 0 gates

- M0.1 OPEN: actual pinned-host native plugin installation/loader/CLI/slash/tool/lifecycle tests and supported ABI floor. SDK source inspection is not native integration proof.
- M0.2 PARTIAL/BLOCKED for authentic operation execution: verifier and denial/replay primitives tested with EPHEMERAL EVALUATOR KEYS in disposable containers; that does not authenticate Sahil or establish public CLI/gateway callers. A real owner-controlled signing key must remain outside both model access and candidate mounts. Owner key enrolment, an owner-signed exact-operation grant and the complete trusted-runner route must be demonstrated before enabling general engine execution. Do NOT generate an agent-accessible key and call its signature owner approval. Missing authority stays refused; no raw registry dispatch/private API/TTY flag fallback.
- M0.3 PARTIAL: stated native container profile exercised; timeout/output-limit handling, process-tree termination, immutable snapshot/TOCTOU resistance and broader malicious-build cases still require acceptance coverage. Same-kernel/rootless-daemon compromises and compromised trusted operator/host/plugin are outside the claimed defence.
- M0.4 OPEN: code-modernization's immutable component LICENSE was retrieved and confirms Apache-2.0. A selected comparator was read for reference, NOT copied or executed. Full component/asset/prior-art inventory and conformance negative controls remain open. No claude-security material was accessed or adapted. Public licence/name decisions remain release-gated.
- M1–M9 NOT STARTED: strict complete product schemas/jobs/inventory/evidence receipts, resumable executor, migration proposals, old/new comparison, reports, host interfaces, held-outs/value comparison and release packet. Do not present this checkpoint as the standalone installable Modernisation Engine or the completed plan.

No authentic owner key/credential was read, created, enrolled or persisted. No model experiments, live service restart/change, benchmark migration, merge, public push or installation occurred. Next required human input for the execution-authority demonstration is an owner-controlled PUBLIC verification key only; never provide a private key to an agent. Independent implementation review remains outstanding and was not delegated.

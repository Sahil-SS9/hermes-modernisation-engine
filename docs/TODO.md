# Remaining work — Modernisation Engine

Current state: **PARTIAL / PARKED engineering preview**, not a complete migration engine or release. Requirements: [updated plan](PLAN.md); pickup: [handoff](HANDOFF.md). Code baseline: `b914c6d118584a45736611c93bb772905108acd6`.

Checkbox rule: `[x]` means the exact subcomponent was implemented and exercised at the recorded boundary. An unchecked parent milestone remains open even when some subcomponents pass. Never mark a whole M0–M9 milestone done because a source file exists or a fixture passes.

## Delivered — do not rebuild unnecessarily

- [x] Loadable standalone directory plugin and host-neutral Python core/CLI.
- [x] Real native CLI: status, assess, paged inventory, plan, compare-gaps and report-gaps.
- [x] Matching registered tools/slash handler; force reload and unload removes all tools.
- [x] CLI namespace collision verification against pinned host PR; separate validator recording-handle repair retained as a patch.
- [x] Bounded canonical JSON; duplicate/nonfinite/ambiguous/path-escape refusals.
- [x] Directory-aware source fingerprints; read-only data inspection, no imported repository code.
- [x] Python AST inventory, exact citations, conservative rule candidates and unsupported-language gaps.
- [x] Durable private assessment jobs, idempotency, optimistic revisions, paged detail hashes, read-only queries.
- [x] SQLite v1-to-v2 backup-before-upgrade and restart/readback tests.
- [x] Deterministic data comparator; untrusted receipt data cannot manufacture proven equivalence.
- [x] Bounded proposal validator and separate source-copy candidate primitive; protected edits refused.
- [x] JSON/text/offline escaped HTML reports with explicit missing evidence.
- [x] Owner-public-key verification and durable one-use grants; forged/expired/mismatched/replayed grants refused.
- [x] External operator executor primitive and actual rootless synthetic controls: success, output overflow, timeout with descendant, verified cleanup and replay refusal. Fixture authority ONLY.
- [x] Offline preview wheel and directory archive built, installed/unpacked, native load/checker and CLI smokes exercised.
- [x] 108 owned tests pass; zero failed/error/skipped; lint and native validator pass. Separate canonical host subset: 34 passed. These overlapping/regression scopes are not an additive product test total.
- [x] Isolated walkie-talkie Python 3.14/FastAPI/httpx metadata candidate locally committed; original public repo unchanged.
- [x] Updated plan, preserved original design, handoff, recovery recipes/patches and evidence summaries versioned for private backup. Private GitHub backup is not release approval.

## Bounded trial pickup — 16 October 2026

- [x] Read-only pickup verification completed: recorded engine/original/candidate commits, unchanged executable delta, private visibility, recovery checksums, rootless runtime, pinned images and both inert owner-v2 preflights. No real execution or claim. Exact current request nonces are unclaimed; signatures absent. This closes only the pickup checks, not M0 acceptance.
- [x] Compared all 249 tracked original file bytes to the frozen baseline; unchanged. Candidate byte differences are only CI/Python/dependency/lock metadata. Full filesystem modes and original-only generated files differ and are explicitly retained in the private audit; byte equality is not full identity equality.
- [ ] Real regression remains BLOCKED: authentic signatures absent, and existing v2 runner retains aggregate counts but discards temporary raw JUnit on container cleanup. Review bounded per-case evidence retention and baseline acceptance before candidate execution; any changed argv/environment/executor requires new exact requests and signatures. No SDK/validator defect reopened; no executor change made.
- Private return: `/home/kensei/handoff/agent-plugin-plans/evidence/modernisation-first-upgrade/REPORT.txt`; structured audit `preflight-1792190776554361765.json` in the same directory. Original/candidate/core/ledger unchanged. Actual exits, JUnit and test counts remain unmeasured. No M0–M9 milestone closed.

## V3 runner evidence fix — 17 October 2026 (owner-approved, KENSEI direct)

- [x] v2 requests expired unsigned/unclaimed at 17/10 14:56:45 BST; superseded, not reused.
- [x] Operator-side per-case evidence fix: signed v3 program emits bounded raw JUnit (base64 + SHA-256) to retained stdout; trusted host evaluator checks the exact predeclared 20 testcase IDs, per-case outcomes, counts and warnings; candidate phase requires re-evaluated ACCEPTED baseline evidence before any claim. Engine core, executor, sandbox, oracle, tests and images unchanged (core identity `434ecb3f…`). Archived in `development/recovery/owner-v3/`.
- [x] Fixture self-test 13/13 (stub pytest, no repo code), incl. substituted-name and marker-injection cases that aggregate counts would have accepted. Both v3 preflights PASS inert; negative candidate attempt refused before claim; ledger hash unchanged.
- [x] Real regression run 17/10/2026 under owner-signed one-use v3 grants (baseline first, candidate second; replay refused). Result: PASSES DECLARED SCOPE — exact same 20 testcase IDs, 20/20 passed on Python 3.12.15 original and Python 3.14.8 candidate; zero fail/error/skip; sources unchanged; containers removed. Receipts NOT_PROVEN (process-only); per-case evidence candidate-authored.
- [x] Follow-up (v4, owner-signed, candidate-only, gated on accepted v3 baseline): pytest-asyncio 1.4.0 + starlette 0.52.1 lock (clone commit c6134c2). Result 20/20 passed, same IDs/outcomes, **0 warnings**. Named difference closed. Earlier "anyio downgrade" note was wrong: both locks pin anyio 4.14.2; the 4.15.1 came from the generic baseline image.
- [ ] Optional, owner-gated: PR (not merge) to public walkie-talkie repo with the Python 3.14 metadata + dependency changes so GitHub CI runs the full 3.11–3.14 suite.
- Result: `evidence/modernisation-first-upgrade/RESULT-v3-20261017.txt` and `RESULT-v4-20261017.txt`; artifacts `run-v3-20261017/`, `run-v4-20261017/`.
- Private return: `evidence/modernisation-first-upgrade/REPORT-v3-runner-fix.txt`. No M0–M9 milestone closed.

## Ordered next actions

1. [ ] **Verify before editing.** Follow HANDOFF.md: clean tree, descendant of code baseline, recovery hashes, exact pinned host/image prerequisites. No source changes authorised by merely opening the handoff.
2. [ ] **Finish prerequisite engineering** (M0, strict contracts, state/fencing), using synthetic controls. These coding tasks do NOT require the real benchmark signatures; do not park the entire engineering backlog behind the regression lane.
3. [ ] **Optional bounded real-regression lane, owner gated.** Revalidate request expiry/source/executor/oracle/image. Obtain fresh signatures if requests are expired or drifted; run original baseline first, candidate second, only in isolation. Record actual exits, expected collection, pass/fail/error/skip counts, warnings and raw-output hashes. A 20-test regression pass is not complete behavioural equivalence.
4. [ ] Complete protected evaluator/receipt acceptance and false-proof controls before enabling native run/resume or model orchestration.
5. [ ] Work the remaining milestones below in dependency order; final independent review and owner decision remain mandatory. DIRECT work only; do not spawn agents to satisfy review without a new owner decision.

## Milestones and exact closure requirements

### M0.1–M0.4 — prerequisites remain PARTIAL

- [ ] M0.1: exercise real interactive/gateway dispatch, full lifecycle/deadline/collision behaviour on the selected supported host. Current tests prove native CLI, registry and registered handler only.
- [ ] M0.2: complete authentic approval/denial on every intended side-effect route, caller provenance, cross-profile actor isolation and approved external-adapter integration. No raw dispatch/TTY flag may mint authority.
- [ ] M0.3: full isolation/cancel/parent-loss/recovery/resource matrix; malicious build hooks and all relevant escape paths; explicitly refuse unverified OS execution.
- [ ] M0.4: finish component/file licence and asset inventory, notices and reference semantic conformance beyond seven comparator primitive cases; retain deviations and negative controls. No proprietary security component adaptation.
- [ ] Confirm owner decisions: actual host release/ABI floor, language breadth, public name/licence, allowed model egress/budget and acceptable intentional behaviour differences. No guessed compatibility range.

### M1–M3 — contracts, state and inventory remain PARTIAL

- [ ] M1: implement strict versioned MigrationJob, BusinessRule, ExecutionReceipt, Comparison and ProofReport contracts/schemas. Reject unknown/missing fields and incompatible majors; bind contract/toolchain/environment and all relevant inputs.
- [ ] M2: complete workflow state machine, attempts, checkpoints, cancellation, per-attempt leases/fencing, durable crash recovery and no-blind-replay. Inject failures at every transition and receipt/state transaction boundary; prove stale-writer and duplicate-resume refusal.
- [ ] M2: complete multi-job/module write-scope isolation and cross-profile concurrency tests, budget stops and recovery actions for ambiguous prior execution.
- [ ] M3: dependency/topology semantics beyond lexical imports; reviewed rules, oracle mappings and adequacy/coverage limitations. Named/skip/prose-only tests cannot upgrade business-rule coverage.

### M4–M5 — execution and proof remain PARTIAL

- [ ] M4: frozen protected original/evaluator checks independent of candidate writers; authentic old/new capture; trusted expected collection/skip policy and parser identity; zero/all-skipped/forged JUnit refusal.
- [ ] M4: authenticated receipt acceptance outside model-writable roots, bound to job/attempt/source/candidate/oracle/environment/command/authority. Process receipts alone remain NOT_PROVEN.
- [ ] M4: native run/cancel/resume integration only after authority/isolation/state acceptance. Current native run/resume deliberately refuse.
- [ ] M5: fresh held-outs, boundary/malformed/state/side-effect/concurrency/property controls; seeded behavioural mutations and comparator self-mutation tests.
- [ ] M5: typed owner-approved field-specific masks/tolerances and accepted-difference catalogue; allow a legitimate narrow case while refusing broad/overlapping canary-erasing normalisation.
- [ ] M5: rule tracing and scope-qualified proof based on stored verified receipts; compare CLI/tool must recompute without subprocess/model calls. Stale/missing/cross-job evidence stays a visible gap.

### M6–M7 — orchestration and full journey remain PARTIAL

- [ ] M6: offline bounded optional patch/model lane, validated structured client, malformed/parsed=None/outage/injection tests; no direct model authority.
- [ ] M6: bounded retry/calls/tokens/time/output budgets, unknown-cost honesty, disjoint batches and circuit breaker; owner egress approval before real model calls.
- [ ] M7: actual assess → baseline approval/capture → plan review → candidate build → candidate authority → comparison → private report journey through intended public surfaces.
- [ ] M7: report `--out` private export, stable evidence links, provenance/count reconciliation, explicit approved differences and surface/caller provenance. Current report returns gap data/HTML, not complete execution proof.
- [ ] M7: independent module/framework migration fixtures as well as the approved walkie-talkie regression candidate.

### M8–M9 — OPEN, not done

- [ ] M8: full native host/settings/cancellation/error UX and supported Python/platform matrix. Linux fixture execution is not macOS/Windows evidence; UI is optional and currently absent.
- [ ] M8: upgrade/rollback/export/reinstall/uninstall preservation and incompatible-schema refusal on actual host paths.
- [ ] M9: predeclared matched ordinary/faithful/enhanced experiments, held-outs, repeats, cost/reproducibility honesty and research ablations. Real/paid runs require explicit budget/egress approval.
- [ ] M9: independent implementation review and correction verification. The original plan review is NOT an implementation review; do not self-certify independence.
- [ ] M9: source/licence/private-data audit, checksummed final artifact and owner INSTALL/DEPLOY/PUBLISH decisions. Private checkpoint push grants none of these.

## Original falsification matrix — all full acceptance items still open

The original plan's §6 defines MT01–MT18. Retain every requirement; current tests cover portions, not every complete matrix item.

| ID | Current coverage | Remaining acceptance |
|---|---|---|
| MT01 | Primitive outputs/types/errors/side-effects | Comparator self-mutation and authenticated pairing |
| MT02 | Unsupported broad masking refused | Legitimate signed narrow normalisation and canary controls |
| MT03 | Historical 20-test original baseline | Current full trusted collection/skip/parser negatives |
| MT04 | Untrusted receipt data cannot prove parity | Protected ingestion, forgery/staleness/cross-job tamper matrix |
| MT05 | Bytes/modes/directories fingerprinted | Full config/toolchain/environment and safe-export matrix |
| MT06 | Rootless isolation and synthetic deadline controls | Full escape/build-hook/OS/crash matrix |
| MT07 | Authority unit refusals and native run denial | Every real side-effect caller route |
| MT08 | Lexical assertion candidates stay unreviewed | Full owner-review/adequacy/executed-rule semantics |
| MT09 | Assessment restart/revisions | Whole state-transition crash/fencing/recovery |
| MT10 | Concurrent idempotent assessment create | Module/batch/resume/concurrent receipt isolation |
| MT11 | No model lane enabled | Real structured schema/client failure controls |
| MT12 | Process output/time caps | Complete model/batch budget service |
| MT13 | Original tests preserved | Protected fresh evaluator and mutation/weakening controls |
| MT14 | Escaped deterministic gap report | Full verified counts/evidence links/approved differences/export |
| MT15 | Fresh load/reload/tool unload | Full host lifecycle/settings/disable routes |
| MT16 | Actual Linux fixture execution | Claim-qualified native platform/Python matrix |
| MT17 | SQLite v1 backup/upgrade unit test | Full actual-host rollback/export/reinstall preservation |
| MT18 | Read-only native journey and artifact smoke | Full authorised real-repo migration and receipt-only compare |

## Parked security/authority notes

- The older owner baseline signature is consumed. Never reuse it or copy it into this repo.
- Pending baseline/candidate requests live only in the local handoff approval directory. Expiry: Unix 1792245405 (17 October 2026 14:56:45 BST). Re-check time and all bound identities when picking up later.
- A skipped signing question is NOT approval. Signatures only unblock exact regression execution, not remaining coding, model egress, installation or release.
- The original public walkie-talkie repo, live Hermes and other projects—including Skill Foundry—are outside writable scope.

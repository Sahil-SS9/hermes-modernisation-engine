# Development checkpoint — read-only preview and external executor controls

Status: PARTIAL BUILD. This does NOT complete the controlling modernisation-engine specification. The original Phase 0 status/validator notes are historical; new evidence below supersedes their narrower implemented-function lists, not their warnings about missing execution/release gates.

## Actually implemented and exercised

- Duplicate-free, bounded canonical JSON; conservative path/type/depth/size checks.
- Source identity v2: file bytes/modes and included directory paths/modes, including empty directories. Relevant ignored/untracked files remain included; known generated/VCS directories explicitly excluded. Symlinks, hardlinks, special files and known credential filenames refuse. No repository program imported by assessment.
- Python AST inventory with exact citations and explicit unsupported JS/TS/other paths. Assertion locations are candidates, NOT all business rules or reviewed adequate tests.
- Private durable assessment jobs; idempotency and optimistic revisions; 100-item content-addressed detail pages with checked digests; no silent inventory truncation. Real clone: 249 files, 2,139 lexical symbols, 1,552 import references, 1,653 assertion-location candidates, no Python parse errors. All saved pages read back and their totals reconciled.
- SQLite schema v2; read queries use mode=ro, do not create a missing store or rewrite job metadata; explicit/write-time v1 upgrade takes a consistent private backup first. FULL transactions and closed connections. This does not implement complete MigrationJob crash/fencing/resume.
- Real native CLI assess/inventory/plan/status/compare/report. Matching registered tools/slash handler call one service, active profile storage resolves each invocation. Tool cleanup verified on unload/reload. Native `run`/`resume` explicitly refuse. Real gateway slash dispatch still unverified.
- Offline JSON/text/escaped-HTML gap reports. Deterministic case comparison and conservative partial-proof policy; plain caller receipts can never yield PROVEN. Data differences stay explicit.
- Bounded source replacement proposal validator and fresh separate candidate materialisation primitive. Protected tests/oracles/build/manifest paths refuse in that primitive; no overwrite or source writes; planned behaviour changes remain separately gated. No automatic model egress or model repair loop.
- External operator executor primitive: exact authority binding, frozen snapshots, rootless-only runtime, create/start/inspect, bounded streaming, timeout/output kill, cleanup readback and immutable process-only evidence. Native execution wiring and crash recovery remain incomplete.

## Observed tests, not combined/inflated totals

Latest all-owned sandbox suite: 108 collected, 108 passed, 0 failed/error/skipped; same run's lint and actual public checker pass. Evidence:
`/home/kensei/projects/modernisation-benchmarks/control/evidence/development-all-1792072450325203199.json`
`development-lint-1792072450818557932.json`
`development-validate-1792072456597459585.json`.

Real external executor controls run in rootless Docker using EPHEMERAL FIXTURE authority only: success case checks read-only source, no host home/socket/credentials/network and exact argv including --rm; overflow retains exactly 1,024 bytes and flags truncation; timeout with a descendant exits 137 and confirms whole-container removal. Durable nonce claims read back and replay refused. Every receipt remains observed-process-only / NOT_PROVEN. Evidence: `/home/kensei/projects/modernisation-benchmarks/control/executor-platform/run-1792072259644658325/summary.json`. These are three mechanism controls, not three real migration tests.

Correction/deviation: an initial operator-only control run used the existing live Hermes interpreter solely to obtain its cryptography verifier dependency (no install/config changes and no untrusted repo code executed there). This was not a suitably isolated project dependency environment. A dedicated `/home/kensei/projects/modernisation-benchmarks/control/operator-env` (Python 3.12.3, cryptography 50.0.1) was created and the exact controls rerun successfully there. Future operator checks use that dedicated environment. No claim of zero deviations.

Canonical host runner repair: real `scripts/run_tests.sh` now runs on a disposable container-owned copy with writable work/cache paths and exits 0 with 34 selected validator cases passed. Existing source mount and live checkouts remain read-only. `/home/kensei/projects/modernisation-benchmarks/control/evidence/canonical-disposable.{json,log}`.

TDD honesty: JSON, identity, store, service, inventory, comparator, sharding, readonly-query, store upgrade/backup, proposal, proof and report functionality each had an observed failing acceptance before the related fix. Initial executor implementation preceded its tests; only subsequent output-storage/empty-directory/exact-argv regressions have witnessed RED. Streaming fixture controls and extra report hardening were added against existing code; no RED is claimed for those. Reference seven-case tests were run against independently authored data semantics; they do not claim the full reference suite passed.

## Working artifacts

Wheel (standalone core/CLI) and directory-plugin ZIP were actually built offline and extracted by SHA-256. Wheel was installed in a clean disposable venv, source PYTHONPATH removed, assess/status roundtrip exercised and run refused. Directory ZIP was unpacked, passed actual native checker and loaded through a fresh isolated Hermes profile. No tests, raw evidence, approval files or private reference cache in the directory artifact. Evidence: `development-build-1792072507625698193.json`.

Artifacts and private assessment HTML are checksummed in the external artifact manifest. They are engineering previews, not a completed engine/release. No live install, push or merge.

## Real candidate and owner boundary

Original `/home/kensei/repos/hermes-walkie-talkie` stays clean on main at `bdbc72300bb494a393992bf4b49259c06811c2b9`.
Isolated candidate `/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie` is on `test/modernisation-fastapi`, local commit `cc191ca18e7529097c2cb3095ca8b803957f5598`, no remote. Only pyproject/lock/CI metadata changed. Python 3.14 bound/classifier/matrix, FastAPI 0.133.1 and httpx 0.28.1; existing other lock versions retained. Original tests/auth/logic untouched. New candidate dependency image was prepared without installing or running project code; no candidate behavioural run claimed.

Fresh owner requests are prepared at `/home/kensei/handoff/agent-plugin-plans/approvals/walkie-v2-1792072605580412472/`. Baseline request SHA-256 `78ff9883666ab5d88aa28d29f88000ed591c9492c69bc29e1d6825eebc322ab4`; candidate request SHA-256 `198cbaaf1a7d7547732acac1cb97184d169888e6412704c29fed28edfef60d5a`. Expiry 1792245405 Unix seconds; each maximum one use. A signature is pending, not implied by prior chat BUILD approval. Prior consumed baseline signature MUST NOT be replayed. Any executor core/source/oracle/image/argv/phase/environment drift requires a newly reviewed request.

## Remaining build gates — NOT all solved by signing

Fresh signatures unblock the real original/candidate regression slice only. Remaining independent engineering includes full strict MigrationJob/BusinessRule/receipt/comparison contracts and schemas; crash-transition/fencing recovery; complete public/external authority-route integration and gateway dispatch; protected fresh oracle/adequacy and authenticated receipt acceptance; legitimate approved mask/tolerance lane and self-mutation detection; bounded optional model/budget/batch service with real structured-client acceptance; full native end-to-end and platform/upgrade matrix; reference licence/semantic audit and research/value trials; independent implementation review. M0–M9 are not being marked complete based on these partial primitives. Model calls/research experiments, supported-host/public licence choices and live/public changes remain separately owner-gated.

Do not claim the entire engine is complete or that signatures are the only remaining work. Resume at the explicit gate, preserve failed receipts, do not execute real benchmark code unsigned, and never install the preview into live Hermes as a shortcut.

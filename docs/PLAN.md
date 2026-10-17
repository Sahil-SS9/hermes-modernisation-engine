<!-- CURRENT POSITION: 2026-10-15 PRIVATE CHECKPOINT -->
# Current position — 15 October 2026

Status: PARTIAL BUILD / PARKED. The engine is an engineering preview, NOT a completed migration system.

This current-position section and `docs/TODO.md` reconcile implementation status; the original design below remains the requirements authority. Completed subcomponents do not close their parent milestone. Nothing below changes the safety requirements or grants execution authority.

Read first (paths relative to the engine repository):
1. `docs/HANDOFF.md` — verify state and resume safely without conversation history.
2. `docs/TODO.md` — checked-off delivered components, open milestones and next actions.
3. This plan — full preserved requirements and original test matrix.
4. `docs/development-checkpoint.md` and `docs/evidence/checkpoint-2026-10-15.json` — producing code/evidence scope.

Repository: https://github.com/Sahil-SS9/hermes-modernisation-engine (private checkpoint authorised; not a public release).
Local repository: `/home/kensei/repos/hermes-modernisation-engine`, branch `build/phase0`.
Executable code baseline: `b914c6d118584a45736611c93bb772905108acd6`; later handoff commits are documentation/recovery-only unless explicitly recorded otherwise.

## Completed components (not full milestone acceptance)

- [x] Native preview plugin load/status/assess/inventory/plan/compare/report and registration cleanup.
- [x] CLI collision fix verified on pinned PR head; separate local validator recording-handle patch verified.
- [x] Strict bounded JSON and directory-aware source fingerprints.
- [x] Private assessment jobs, paged inventory, idempotency, optimistic revisions, read-only queries and backup-before-upgrade.
- [x] Conservative Python lexical inventory with exact citations and visible unsupported-language gaps.
- [x] Data comparison, refusal to upgrade untrusted receipt data to proof, escaped offline reports.
- [x] Bounded patch proposal and separate candidate-copy primitives.
- [x] External one-use signature verification and real rootless synthetic executor controls (output cap, deadline/descendants, cleanup/replay refusal).
- [x] Offline preview wheel/directory build and installed artifact smoke; 108 owned tests pass with zero failures/errors/skips, lint and native validator pass.
- [x] Isolated Python 3.14/FastAPI benchmark candidate prepared and committed locally; original public walkie-talkie repo untouched.

## Milestone reconciliation

| Milestone | Current status | What keeps it open |
|---|---|---|
| M0.1 | PARTIAL | Real gateway/interactive route and full lifecycle/deadline acceptance |
| M0.2 | PARTIAL / OWNER GATE | Full intended caller/executor authority routes; fresh exact real-run signatures |
| M0.3 | PARTIAL | Full isolation/cancel/crash matrix; no unsupported OS execution claims |
| M0.4 | PARTIAL | Full licence/asset and comparator semantic audit; selected reference cases only completed |
| M1 | PARTIAL | Full versioned MigrationJob/BusinessRule/receipt/comparison/report schemas |
| M2 | PARTIAL | Complete state machine, attempt leases/fencing, fault-injected restart/recovery |
| M3 | PARTIAL | Reviewed rule/topology semantics and adequacy, not lexical extraction alone |
| M4 | PARTIAL | Protected current baseline/candidate capture, trusted evaluator and receipt acceptance |
| M5 | PARTIAL | Fresh oracle/mutation controls, signed legitimate normalisation/tolerances and rule tracing |
| M6 | PARTIAL | Bounded optional model/budget/batch orchestration and real structured-client acceptance |
| M7 | PARTIAL | Full authorised assess-to-private-report journey, including execution and stored-receipt comparison |
| M8 | OPEN | Full native/supported-platform/settings/cancellation/upgrade matrix |
| M9 | OPEN / OWNER GATE | Independent implementation review, approved matched experiments and release sign-off |

## Bounded trial pickup — 16 October 2026

Read-only pickup checks pass on the recorded engine/original/candidate commits and pinned rootless images; production bytes remain unchanged from the preview baseline. Both inert owner-v2 preflights return no execution/no claim. Requests were still unexpired and unclaimed at capture; no signatures were provided. All 249 tracked original files match the frozen baseline bytes. Candidate byte changes remain the three metadata files, with physical mode/generated-file differences retained separately rather than masked.

The bounded trial is **BLOCKED, NOT RUN**. In addition to missing authentic signatures, the existing v2 argv leaves raw JUnit only in disposable container `/tmp`; aggregate stdout counts cannot supply the required retained per-case collection evidence. Review minimal bounded evidence retention and baseline acceptance before candidate execution. Changed execution identities require new exact signed requests. No host/core/validator/executor patch, benchmark execution or parent-milestone completion occurred. Safe audit/report only: `/home/kensei/handoff/agent-plugin-plans/evidence/modernisation-first-upgrade/REPORT.txt` and `preflight-1792190776554361765.json`. The original design below is preserved.

**Update 17 October 2026.** The v2 requests expired unsigned and unclaimed. With owner approval, the evidence prerequisite is closed by an operator-side v3 runner: the signed program also returns bounded raw JUnit, and a trusted host evaluator checks the exact 20 predeclared testcase identities before the candidate may run. Engine core/executor/sandbox/oracle/tests/images are unchanged. Fresh v3 requests await authentic owner signatures (`approvals/walkie-v3-1792267598341426808/`, expiry 19/10/2026 21:06 BST). Evidence remains candidate-authored per-case JUnit, NOT_PROVEN at receipt grade. See `REPORT-v3-runner-fix.txt`.

**Result 17 October 2026.** Owner signed; trial ran baseline first, candidate second. The selected upgrade **PASSES THE DECLARED 20-TEST API/AUTH REGRESSION SCOPE**: identical testcase set and per-case outcomes, 20/20 on both Python 3.12.15 and 3.14.8. Named difference: warnings 1 → 1237, all third-party Python-3.16 deprecations (pytest-asyncio 0.24.0, starlette), not application code. Not equivalence, not automated migration, not M4 acceptance; no milestone closed. See `RESULT-v3-20261017.txt`.

## Immediate next step and holds

1. Re-verify repo, code ancestry, private recovery payload hashes and local prerequisites. Follow `docs/HANDOFF.md`.
2. Decide what resumes first: complete missing prerequisite safety/schema/state work with fixture controls, or obtain fresh exact signatures for the bounded real regression lane. Signing is NOT a blocker to every remaining coding task.
3. Only with current authentic signatures, execute original then candidate in isolation. Prior baseline grant is consumed. Pending requests expire at Unix 1792245405; if expired or any bound identity changed, regenerate and obtain new owner approval. Never blindly run a parked command months later.
4. Work remaining phases in dependency order; preserve failed evidence. Complete M0 acceptance before enabling dependent native/model execution.

Locked: DIRECT implementation only, no workers/delegation. No live installation/config/restart, original-repo changes, public release or model egress/paid experiments without separate approval. This owner's private-repo push permission is a backup/checkpoint exception only; earlier no-public-push restrictions remain. Do not import unrelated Skill Foundry work or its pin into this engine.

Original design follows verbatim. Its planning-only statements and proposed commands describe the original planning event, not current implementation results; current verified status is above and in the linked checklist.

<!-- ORIGINAL DESIGN BELOW — PRESERVED VERBATIM -->

# Modernisation Engine — standalone plugin build plan

Status: final planning handoff, source-revalidated and independently reviewed (revision 1). NOT approved for implementation, installation, deployment or publication.

## Product decision

Build an engine that turns an existing repository and an owner-approved migration target into an isolated candidate plus a reproducible old/new behavioural evidence report. A faithful Hermes adaptation already has value; additional continuous assessment, multi-model critique and reusable playbooks must earn their value in measured trials. Do not reduce the full vision to a refactoring prompt, or claim complete equivalence from a few green tests.

Primary users: people building/running agents who need dependency/runtime upgrades, architectural changes and framework/language migrations. Default operation is read-only assessment. Changes stay in an approved candidate worktree; preserving behaviour means preserving the declared contract, not silently preserving or repairing every legacy bug.

Standalone boundary: this plugin owns migration planning, candidate execution checkpoints and old/new comparison. It does not require Code Assurance or Agent Run Debugger to succeed. Integrations with either are later optional adapters.

## Ownership, authority and isolation

- Owner: Sahil. Author/final judgement: KENSEI. This document authorises planning only. It does not authorise implementation, installs, model experiments, configuration changes, public writes, deployment or automatic promotion.
- Each engine is a separate native Python Hermes plugin and independently installable repository/package. Its domain core is host-neutral; Hermes is the first complete adapter. No required sibling plugin, shared database, central orchestrator, daemon, fleet profile, memory provider, Project Stewardship/HPS installation or private paper archive.
- Use the current public plugin SDK. Do not patch Hermes core, monkeypatch registries, override built-in tools, read stored credentials, create profiles or invent capability IDs. Plugins are trusted in-process code; the manifest is not an OS sandbox.
- A disposable worktree or temporary directory is not security isolation. Untrusted program execution requires a separately verified OS isolation backend. If none is available, expose read-only/import functions and report execution as unavailable; never silently fall back to unsafe execution.
- Source files, repository instructions, imported traces, model output and model-proposed approval messages are untrusted data, not authorisation. Approval authority must originate outside the model-writable candidate workspace. A hash binds content but does not authenticate the approving person.
- No automatic merge, deployment, publishing, credential/fleet changes, deletion of user sources, or self-promotion of generated skills. BUILD, INSTALL, DEPLOY and PUBLISH are separate owner gates.
- Public redistribution must exclude private persona builders, benchmark suites, corpus, fleet configuration, credentials and user traces. Reuse of existing private tools is for internal development only unless the owner separately changes that policy.

## Source baseline and retrieval contract

Planning reference date: 2026-10-14. Pins are evidence baselines, not a claim that future upstream HEAD will be identical.

- Anthropic source A: https://github.com/anthropics/claude-plugins-official/tree/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3 . The read-only source inspected here was `/home/kensei/.hermes/cache/scratch/claude-plugins-review-6dnkv47q/source`; scratch is not a durable dependency. Reconstruct the pinned source in an isolated planning/build workspace if that cache has expired.
- Hermes source H: https://github.com/NousResearch/hermes-agent/tree/0e427d788d253630d38a3a51cd76849e73cd6925 . Parent verified its Git objects locally. The vanilla checkout HEAD was older `8c098e9e819169879a7b2f74990e83b5d39696c8`; do not mistake checkout files for H. Read exact files with `git show 0e427d788d253630d38a3a51cd76849e73cd6925:<path>`, or retrieve immutable GitHub contents. No edits to the vanilla checkout.
- Official live docs: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins ; https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access ; https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks ; https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission . Docs can drift; record retrieval date and resolve conflicts against the target version's source and an actual host smoke test.
- H public API reference: https://github.com/NousResearch/hermes-agent/blob/0e427d788d253630d38a3a51cd76849e73cd6925/hermes_cli/plugins.py ; storage https://github.com/NousResearch/hermes-agent/blob/0e427d788d253630d38a3a51cd76849e73cd6925/plugins/plugin_storage.py ; model facade https://github.com/NousResearch/hermes-agent/blob/0e427d788d253630d38a3a51cd76849e73cd6925/agent/plugin_llm.py ; consent https://github.com/NousResearch/hermes-agent/blob/0e427d788d253630d38a3a51cd76849e73cd6925/hermes_cli/plugin_capabilities.py .
- Component licence rule: the repository is not uniformly Apache. Check the licence beside every component before copying. `plugins/claude-security/LICENSE` is proprietary and forbids redistribution/non-Anthropic product use. Exclude ALL its code, prompts, workflows, schemas and documentation from adaptation; this plan must not translate that plugin. Applicable licence notice only: https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/claude-security/LICENSE . Use independently authored requirements and permissively licensed components. Preserve Apache attribution/NOTICE where applicable, mark adaptations, and audit bundled third-party assets separately.

## Public Hermes integration facts verified during planning

Source H establishes:

- Native directory plugin: `plugin.yaml` plus an `__init__.py` exposing `register(ctx)`. Pip entry-point discovery is also available. Pick one distribution path for v1, not two competing runtime registrations.
- `ctx.register_tool(name, toolset, schema, handler, ...)` and `ctx.register_command(name, handler, description=..., args_hint=..., argument_mode=...)` are separate registrations. Slash handlers receive `raw_args`; CLI has `ctx.register_cli_command(name, help, setup_fn, handler_fn, ...)`. Do not confuse `hermes <name>` with `/name` or shadow `hermes verify`/`/verify`.
- `ctx.dispatch_tool(tool_name, args, **kwargs)` dispatches through the host registry. Parent-agent resolution differs in gateway mode. It is not proof that every invocation route inherits the same approval context: test agent, CLI, slash and gateway call sites. Missing authority means no side effect.
- `ctx.llm.complete(...)` / `complete_structured(...)` use host-owned model access. Overrides require independently granted gates. The facade is bounded completion, not a tool-running autonomous worker. Validate every returned schema locally; structured parsing can be absent and source validation depends on an optional dependency. A model's answer is evidence to investigate, never a test receipt.
- `plugin_data_dir(name)` follows active Hermes home on every call; do not cache a global path across profiles. `plugin_db(name, filename)` supplies storage helpers, not cross-process transaction semantics. Resolve scope per operation; own locking, migrations and cleanup rules.
- Capability consent covers existing enforcement gates such as model/provider overrides and platform actions, not arbitrary filesystem/network sandboxing. The v1 manifest declares only real capabilities it actually needs, with optional overrides off.
- Host source declares Python `>=3.11,<3.15`, but its pyproject version is `0.0.0`; infer neither supported release floor nor Desktop compatibility from that value. Establish the release/ABI floor in Phase 0 through actual supported-host installation tests.

## Handoff protocol for the future implementation agent

1. Read this file in full. Record source pins, proposed interfaces and unresolved decisions. Do not rely on the previous chat or transient subagent transcripts.
2. Obtain BUILD approval and a concrete first benchmark/project before making implementation changes. Budget/model egress and INSTALL approval are separate. Work in this plugin's own repository/worktree; never edit the source references or siblings.
3. Complete Phase 0 compatibility, licence and threat-boundary spikes. A failed seam is a recorded blocker, not permission to add a core patch, hidden service or approximate substitute.
4. For each task: witness the relevant RED test, implement the minimum behaviour, run targeted GREEN and the complete owned suite, then record commands, exit status, collected/pass/fail/skip totals and immutable input/output identities. Do not invent test output.
5. Stop at review gates. Reconcile independent findings and rerun the affected checks. Request owner approval for scope changes, new providers/cost, privilege/isolation changes and public release.
6. Final handoff must contain a working installable artifact, actual host/interface execution, known limits, private evidence bundle, attribution inventory and reproducible commands. Passing this plan review is not passing implementation tests.

## 1. Scope, users and release shape

Working identifiers (proposed; verify collisions in Phase 0): repository `hermes-modernisation-engine`, Python package `hermes_modernisation`, plugin id `modernisation-engine`, native CLI `hermes modernise`, slash `/modernise`, tools `modernise_assess`, `modernise_plan`, `modernise_status`, `modernise_compare`, `modernise_report`, plus `modernise_run` for the same authentic-grant-gated execution service as CLI `run`. `modernise_run` is disabled until public authority and isolation gates pass; resume remains an explicit CLI/slash operation, not an implicit side effect of status. All state belongs to `plugin-data/modernisation-engine/` for the current profile. A tool that can cause a mutation must be a distinct, gated operation, not an undocumented mode of a read-only tool.

User journey:

1. Select a repository, declare the upgrade/rewrite goal and the relevant behaviours.
2. Receive an inventory, extracted rule candidates, dependencies, execution prerequisites and known unknowns.
3. Review the intended contract, protected oracle/tests, planned differences, scope and budget. This first review may grant baseline execution only; it does not approve the later migration or candidate execution.
4. Rehearse old behaviour under a trusted harness; if it cannot run, explicitly stop equivalence proof.
5. Produce a candidate in a separate authorised workspace and compare the same declared inputs under old/new environments.
6. Receive a patch/candidate, reproducible private evidence, tested-rule mapping, accepted differences, unverified gaps and rollback/handoff instructions. No automatic merge.

The first complete release must work end-to-end on at least one real approved project, plus evaluator-owned fixtures for a runtime/dependency upgrade, a framework change and a service/module rewrite. It is not a claim of universal multi-language migration. Maintain an adapter support table: language/runtime, old/new runner, build/test parser versions, sandbox backend, proven test cases and unsupported behaviours. Python plus one second ecosystem is the proposed early validation breadth; exact projects are an owner decision before BUILD, not a licence to shrink the product indefinitely.

Later depth: repo-wide dependency-aware batches; more language/framework adapters; periodic READ-ONLY drift assessment; before/after topology and impact views; opt-in cross-model critique; owner-reviewed reusable migration playbooks. Never turn continuous assessment into scheduled automatic rewrites. Proposed opportunities become proposals, not automatic live changes.

Non-goals: a new marketplace, fleet scheduler, global approval service, general-purpose agent framework, mandatory SaaS, universal semantic-equivalence theorem, automatic production cutover, or replacing sibling engines. No inherited private builder/test/corpus dependency.

## 2. Foundation: exactly what to reuse and what to replace

Abbreviated `scripts/`, `commands/`, `agents/`, `workflows/`, `hooks/` and `assets/` paths in the matrix are relative to `plugins/code-modernization/` in immutable source A. Read component-local `plugins/code-modernization/LICENSE` first; it is Apache-2.0. Preserve its licence, applicable notices, copyright and adaptation provenance. Do not assume other marketplace plugins share this licence.

| A component | Proposed disposition | Reason and limitation |
|---|---|---|
| `plugins/code-modernization/scripts/compare.py` | Adapt after conformance tests | Deterministic comparison, masks/tolerances with reasons, self-check and atomic output. Its inputs and tolerance policy are not an authorisation mechanism. |
| `scripts/proof_pack.py` | Adapt verdict discipline; re-home/version the contract | Recomputes from case/result evidence rather than trusting report prose. File timestamps and fixture names are weak provenance; supplement with trusted-run identity and input digests. |
| `scripts/trace_rules.py` | Adapt with conservative semantics | Distinguishes executed/named/prose-claimed rules. A passing test named after a rule does not prove that rule's assertions are adequate. |
| `scripts/baseline_diff.py`, `scripts/uplift_checks.py` | Adapt selected parsers and comparisons | Preserve unmeasured/unsupported outcomes. Test-file changes can be detected; universal detection of weakened assertions is not provided. |
| `scripts/make_shards.py`, `scripts/render_rules.py` | Adapt relevant containment/formatting checks | Keep raw-path validation before normalisation and reject symlink/escape ambiguities. |
| `scripts/tests/test_proof_tools.py` and neighbouring test assets | Adapt compatible assertions into this plugin's OWN suite | Reference fixtures are conformance input, not evidence that a new implementation works. Add host, receipt-authenticity and OS-isolation tests. |
| `commands/*.md`, `agents/*.md`, `workflows/*.js` | Re-author Hermes orchestration | JS fan-outs/tool names require Claude runtime. Retain useful dependency/disjoint-scope/circuit-breaker concepts, not unsupported runtime calls. |
| `hooks/sign.ts` | Do not port | Writing “Approved by” into a model-writable Markdown file is not trustworthy approval. |
| `hooks/register.ts`, pane readers and React views | Replace only if needed via Hermes SDK | Experimental Claude UI hooks are not Hermes APIs. A report is enough for the first end-to-end release; richer views are later. |
| `scripts/build_report.py`, HTML assets | Independently render validated evidence | Keep recomputation as an invariant; no branded/experimental UI dependency. Mermaid, if bundled, has its own MIT notice and must be audited separately. |
| `scripts/telemetry.py`/shell wrappers | Exclude from core port | Do not introduce unsolicited telemetry or a second billing/control plane. |

Shared-source conformance note: Modernisation and Code Assurance may independently adapt the same permitted proof/comparison primitives. Each OWN provenance ledger records shared ancestry, upstream pin, retained negative-control fixtures and any intentional semantic divergence. Keep conformance changes visible across the two plans without a runtime sibling dependency; extracting a shared library is a later owner decision, not an unapproved dependency.

Relevant reference guide and proof tests:

- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/README.md
- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/LICENSE
- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/scripts/compare.py
- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/scripts/proof_pack.py
- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/scripts/tests/test_proof_tools.py
- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/workflows/uplift-migrate.js
- https://github.com/anthropics/claude-plugins-official/blob/8bd00f08f0b04705e610cf132fbe2cf5ec44cfe3/plugins/code-modernization/hooks/sign.ts

Additional paths in the matrix are resolved against A verbatim. Record SHA-256 of each adapted file and the exact upstream tests retained in `docs/provenance.md`; do not execute it before source/security review and the appropriate sandbox approval.

Prior-art pointers at H: `plugin-catalog/hades-coding-workflows.yaml` (workflow skills; advertised repository SHA `b68546d66fe684a49633a9174e44362eff77cbfc`) and `plugin-catalog/crew.yaml` (coordinated verified work; repository SHA `2485e745f756da366db6943ff46b7e9c31f31ed9`). These catalogue descriptions are not independently tested capabilities. Phase 0 reads their pinned product documentation and records overlap. Differentiation hypothesis: executable old/new contracts, migration-specific evidence and resumability, not merely multi-agent orchestration. If prior art already covers the intended outcome, present an adaptation/interop option to Sahil rather than build a duplicate by default. Neither product is a required dependency.

## 3. Architecture and module boundaries

```text
hermes-modernisation-engine/
  plugin.yaml                    # native manifest, supported config fields, real capabilities
  __init__.py                    # register(ctx); thin, no work/network/model call at import
  pyproject.toml, uv.lock         # proposed managed development environment; lock created after BUILD
  LICENSE, NOTICE, THIRD_PARTY_NOTICES.md
  src/hermes_modernisation/
    contracts.py, jsonio.py       # versioned strict schemas, size/depth/type limits
    inventory.py, topology.py    # bounded repo inventory, caller/dependency references
    rules.py                     # candidate rules + evidence/status, never semantic-certainty score
    state.py, store.py            # durable jobs, transactions, idempotency, profile resolution
    identity.py                  # relevant source/test/config/environment/toolchain digests
    approvals.py                 # opaque host/owner grants; no agent “approve” endpoint
    runner.py, sandbox.py         # declared execution contract, isolation preflight, kill/cancel
    compare.py, baseline.py       # old/new executions + authorised normalisation
    proof.py, rule_trace.py       # rederive per-scope conclusions and gaps
    batches.py                   # dependency order, disjoint writes, bounded circuit breaker
    proposals.py                 # structured patch proposals validated before deterministic application
    report.py, cli.py             # JSON + plain-text/Markdown report + standalone CLI
    adapters/hermes.py           # public PluginContext, model and storage mapping only
    adapters/runners/            # explicitly supported language/toolchain adapters
  schemas/                       # job, plan, rule, execution receipt, evidence and report schemas
  skills/modernise/SKILL.md       # consumer workflow; not a private persona/factory import
  tests/unit/, tests/adversarial/, tests/integration/, tests/host/, tests/platform/
  tests/fixtures/                # clean/broken/sample programs, deterministic offline model stubs
  scripts/checks.sh              # future local full gate; does not auto-install globally
  docs/compatibility.md, docs/provenance.md, docs/threat-model.md
```

Core ports: `RepoReader`, `ModelProposer`, `ExecutionAuthority`, `IsolatedRunner`, `EvidenceStore`, `ReportRenderer`. No Hermes import below `adapters/`. Model output is a typed proposal; it has no direct filesystem/tool-execution/approval authority. The runner and evidence collector are trusted components outside the writable candidate. A host-neutral manual adapter may be offered, but its receipts must be labelled self-reported unless an approved trusted executor actually collected them.

### Execution authority — mandatory Phase 0 release blocker

Parent source validation found `ctx.dispatch_tool` calls `tools.registry.registry.dispatch`, which directly invokes a handler; this is NOT equivalent to `AIAgent.handle_function_call`'s complete policy/hook path. Do not use it as an assumed approval wrapper. References at H: `hermes_cli/plugins.py:674–683`, `tools/registry.py:893–921`, `hermes_cli/plugins_dispatch.py:211–245`.

`ctx.register_approval_transport` registers a presentation transport selected by host security configuration; it does not itself mint a policy approval. The first spike must demonstrate a PUBLIC host-supported request/response path that binds an authentic owner decision to the exact operation and then reaches the executor on CLI and gateway. Required grant fields are proposed: job/attempt, source+candidate+contract digests, allowed paths/argv/env/network, expiry, usage limits, requesting identity and approving origin. Only the trusted adapter constructs the grant; never accept these fields as caller-provided proof.

If such a public route cannot be demonstrated at the target version, execution stays disabled and the owner must approve either a documented external trusted executor adapter or an upstream API improvement. Do not silently import private internals, treat a TTY/CLI flag as actor authentication, build a global approval system, or call raw dispatch/subprocess as a workaround. Hash chains alone do not prevent a malicious writer with access to the authority store. Specify the trust boundary in the threat model; no defence is claimed against a compromised trusted host/plugin/owner account.

### Isolation

Legacy sources are frozen by digest and mounted read-only by the verified runner; a symlink labelled “legacy” is not a read-only mount. Candidate, oracle and runner live in separate permission scopes. Default network off, no inherited provider credentials, allowlisted environment, capped processes/memory/output/time, explicit dependency caches. Test scripts and build hooks are executable code. Linux is the first proposed fully executed sandbox backend; macOS/Windows read/import/report may work earlier, but execution is explicitly UNSUPPORTED until their isolation drivers and native tests pass. No mandatory always-on daemon. Exact backend choice is an owner-reviewed Phase 0 result, not a promised capability of Hermes.

## 4. Contracts, verdicts and resumable workflow

All schemas below are proposed product interfaces, not existing Hermes APIs. Files are versioned; incompatible major versions refuse rather than reinterpret evidence.

`MigrationJob v1`: job id; requested goal and track (`uplift`, `transform`, `reimagine`); current profile scope; source inventory/digest; adapter versions; explicitly supported behaviours; baseline prerequisites; approved difference catalog; protected oracle id/digest; input split+seed; runner/toolchain/env identity; budget; allowed output roots; model/egress policy; operation-authority references; attempts, checkpoints and evidence ids.

`BusinessRule v1`: stable id; source citation; textual candidate; owner review state; linked oracle cases/assertions; coverage status (`extracted`, `reviewed`, `asserted`, `executed`, `unverified`); unknowns. Named/passing tests do not upgrade rule adequacy by themselves.

`ExecutionReceipt v1`: trusted collector identity and origin; job/attempt/check id; inputs/source/candidate/oracle/command/argv/env/toolchain digests; supported isolation profile; start/end and monotonic duration; actual exit/signal; expected/collected/pass/fail/skip counts and parser version; artifact refs/digests; completeness/truncation/error; authority correlation; executed-vs-reported provenance. Store outside model-writable roots. A imported or manually typed receipt is not automatically observed evidence.

`Comparison v1`: baseline+candidate receipt ids; exact input ids and split; output/exception/side-effect projections; masks/tolerances and their authentic approval reference; each raw and normalised difference; comparator self-check; accepted differences kept visible. Approvals to change intended behaviour are separate from approvals to run code.

`ProofReport v1`: per declared module/contract scope `PROVEN_WITHIN_DECLARED_SCOPE`, `PARTLY_PROVEN` or `NOT_PROVEN`; findings and missing evidence; rule adequacy/coverage limitations; approved changes; reproducibility instructions; source/toolchain identities; freshness and authority checks. Never “the whole system is equivalent” from a subset. Internal wording may adapt the reference's PROVEN label, but exported claims MUST include scope.

Workflow states: `CREATED → ASSESSED → BASELINE_AUTHORITY_REQUIRED → BASELINE_AUTHORITY_GRANTED → BASELINED → PLAN_REVIEW_REQUIRED → MIGRATION_APPROVED → CANDIDATE_BUILT → VERIFIED → HANDOFF_READY`. Running legacy code requires its own authentic baseline execution grant BEFORE BASELINED; later migration-plan approval is a different decision and never retroactively authorises baseline execution. Candidate execution likewise needs a current operation grant, not just the global MIGRATION_APPROVED status. Side states: `BLOCKED_PREREQUISITE`, `EXECUTION_UNAVAILABLE`, `AUTHORITY_REQUIRED`, `INTERRUPTED`, `BUDGET_STOPPED`, `FAILED`, `CANCELLED`. Owner sign-off is a separate status; HANDOFF_READY is not merge permission.

Crash/resume: transactionally claim one attempt; persist checkpoints and immutable receipts; leased workers with fencing token; no blind replay of side effects after process loss. On resume, recheck source/candidate/oracle/env/contract hashes and authority expiry. A changed input invalidates dependent evidence only, with an explicit reason. Concurrent jobs never share candidate write scopes. Refuse an ambiguous baseline or unknown prior execution state; expose a recovery action instead.

### Behavioural oracle and false-success prevention

- Compare both implementations on the same independently controlled cases; hold out fresh cases until evaluation. Reference fresh-case minima are inspiration, not a universal coverage guarantee. Proposed early fixture floor: ten fresh inputs PLUS boundary/malformed/state/side-effect cases appropriate to each declared contract.
- Use deterministic seeds, metamorphic/property checks where the contract permits, API/DB/file/network side-effect capture, rollback/transaction/concurrency tests and normalised error semantics. Schema equality/compilation is not business-behaviour equality.
- Explicitly freeze protected tests, oracle, masks and tolerances outside candidate writers. Modified/weakened legacy tests remain visible; run protected original/evaluator checks as well. No algorithm claims complete semantic weakening detection.
- Seed deliberate behavioural mutations. The comparator and oracle must detect them. A canary text note, zero-test exit 0, forged JUnit, stale report or missing legacy execution cannot pass.
- A test runner generated by a model cannot vouch for itself. Capture expected collection and results through a reviewed evaluator-owned harness. Validate both ordinary positive cases and false-positive negatives; disclose limits against hostile programs that can spoof their own logs.
- Mask/tolerance requests are typed proposals with field-level scope, caps and reasons. No blanket wildcard masking or “normalise until green”; broad/overlapping masks that erase a mutation must be refused. Display accepted semantic changes in the final report.

## 5. Implementation sequence and dependency gates

Each task uses RED → minimum implementation → targeted GREEN → full owned suite → evidence. Planned commands are in §8 and are NOT claimed executed now.

| Task / deps | Files | First RED / acceptance | STOP condition |
|---|---|---|---|
| M0.1 / BUILD approval | `docs/compatibility.md`, minimal manifest/entrypoint, `tests/host/test_loader.py` | Real pinned-host install-alone/load/CLI/slash/tool registration, collision refusal, reload/unload under load deadline | Missing public route/API or silent registration failure |
| M0.2 / M0.1 | `adapters/hermes.py`, `approvals.py`, `tests/host/test_authority_routes.py` | Authentic denial/approval on every intended side-effect route; forged tool args/CLI approval rejected | Raw dispatch or model text can manufacture permission |
| M0.3 / M0.1 | `sandbox.py`, `docs/threat-model.md`, `tests/platform/test_isolation.py` | No legacy writes, escape/network/credential/process-tree leak; native OS claim tested | Temp directory treated as sandbox or unsafe fallback |
| M0.4 / reference audit | `docs/provenance.md`, notices, `tests/integration/test_reference_contract.py` | Licence inventory; baseline comparator conformance incl negative controls; map prior art | Proprietary material or untracked adaptation |
| M1 / M0.4 | `contracts.py`, `jsonio.py`, `identity.py`, schemas | Reject corrupt/deep/oversized/NaN/ambiguous/path-escaping data; every relevant byte affects identity | Unknown fields or incomplete input manifest silently accepted |
| M2 / M1 | `state.py`, `store.py`, `tests/integration/test_resume.py` | Crash after every transition; duplicate/idempotent calls; fencing and cross-profile scope | Duplicate mutation, mixed jobs or lost authority |
| M3 / M1 | `inventory.py`, `topology.py`, `rules.py`, `tests/unit/test_inventory_rules.py` | Bounded reads, executable-config treated as data, exact citations, unsupported-language unknowns | Claim all business rules from lexical extraction |
| M4 / M0.2+M0.3+M2 | `runner.py`, runner adapters, `baseline.py`, protected fixtures | Trusted legacy baseline, collected-test oracle, timeout/cancel; legacy unavailable → NOT_PROVEN | Baseline fabricated or code executed without grant |
| M5 / M4 | `compare.py`, `proof.py`, `rule_trace.py`, adversarial fixtures | Detect mutations, false green, stale receipts, masking abuse, intentional differences | Any planted critical change becomes fully proven |
| M6 / M0.2+M2+M5 | `proposals.py`, `batches.py`, skill, model adapter | Offline bounded patch loop, schema-invalid model output, context injection, disjoint scopes, budget stops | Direct LLM tool authority, unbounded retries/fan-out |
| M7 / M5+M6 | `report.py`, CLI/slash/tools, `tests/integration/test_end_to_end.py` | User completes assess→approve→build→compare→private report without sibling plugins | Report count/provenance disagrees with evidence |
| M8 / M7 | host/platform matrix, optional SDK UI | Real native routes, settings/cancellation/error UX, upgrade/rollback; accessibility if UI included | Stub-only host tests or unsupported OS advertised |
| M9 / M8 | held-out benchmark and release packet | Independent review, measured comparison and owner sign-off | Public claims without replicated evidence or PUBLISH approval |

Long-job policy: durable job state; foreground CLI run/resume/status first. No daemon/cron required. If an optional host-managed background worker is added, explicitly test cancellation, parent-session exit, per-job cap and absence of duplicate resumes; no session-bound delegate task is the durable scheduler.

## 6. Test matrix — required falsification, not just happy paths

| ID | Test location | Fixture / expected result |
|---|---|---|
| MT01 | `tests/unit/test_compare.py` | Same outputs pass; changed bytes/types/errors/side effects fail; comparator self-mutation detected |
| MT02 | `tests/adversarial/test_normalisation.py` | Legitimate timestamp mask works; broad/wildcard/overlap/tolerance overflow cannot hide a canary |
| MT03 | `tests/integration/test_baseline.py` | Collected/pass/fail/skip reconciliation; all-skipped or zero tests, unknown parser, unavailable old runtime stay unproven |
| MT04 | `tests/adversarial/test_receipts.py` | Forged/stale/edited/cross-job/partial receipts, fake JUnit and copied report cannot become observed proof |
| MT05 | `tests/integration/test_identity.py` | Tracked, relevant untracked/ignored/config/fixture/toolchain/env changes invalidate evidence; secret values not exported |
| MT06 | `tests/platform/test_isolation.py` | Symlink/hardlink/traversal/cwd escape, malicious build scripts, network/credential access, child process leak refused |
| MT07 | `tests/host/test_authority_routes.py` | CLI/agent/slash/gateway denial, expired grant, actor mismatch and changed argv remain denied |
| MT08 | `tests/unit/test_rules.py` | Named/prose-only/skip rule claims stay unverified; failed assertion cannot be called covered |
| MT09 | `tests/integration/test_resume.py` | Fault injection at every state transition; restart/idempotency/fencing; changed baseline blocks replay |
| MT10 | `tests/integration/test_concurrency.py` | Parallel jobs/batches do not write same module or mix receipts/profile state; circuit breaker holds |
| MT11 | `tests/adversarial/test_model_lane.py` | Malformed response, parsed=None, prompt injection, forged approval, provider outage and missing schema dependency fail safely |
| MT12 | `tests/unit/test_budget.py` | Calls/tokens/time/output caps stop further work; unknown pricing stays unknown, no invented hard-dollar guarantee |
| MT13 | `tests/integration/test_oracle.py` | Protected held-outs, property/metamorphic/state/concurrency/boundary cases; weakened candidate tests do not substitute for oracle |
| MT14 | `tests/unit/test_report.py` | Schema-valid JSON, escaped HTML, exact totals, stable evidence links, scope qualifier and visible approved differences |
| MT15 | `tests/host/test_lifecycle.py` | Install-alone, enable/disable/reload/unload, registration cleanup, settings isolation and no global mutation |
| MT16 | `tests/platform/test_matrix.py` | Real Linux execution; native Windows/macOS only for claimed features; unsupported sandbox visible/refused |
| MT17 | `tests/integration/test_upgrade_rollback.py` | Schema migration atomic, downgrade/export safe, reinstall data preserved, uninstall no source/user-data deletion |
| MT18 | `tests/integration/test_end_to_end.py` | Full fixture and approved real-repo journeys; authentic host calls, patch/artifact accessible, manual merge gate intact; compare tool/CLI recomputes stored receipts with zero subprocess launches, missing/stale receipts stay gaps |

Add property/fuzz suites to JSON/path/comparison layers, platform-qualified resource limits and repeated fault injection. Tests alone cannot establish semantic completeness; both fixtures and the chosen real-project contract must be reviewed for relevance.

## 7. Validation of product value and research-led improvements

Three matched arms: ordinary Hermes coding workflow; faithful port using allowed reference components; enhanced port with ONE isolated method change. Same task inputs, available tools, model where possible, authority, budget and evaluator-owned oracle. Native Claude reference may be a separate reference run only when its subscription/runtime permission is available; a cross-model/cross-host result is not causal proof of the harness's advantage.

Measure task completion, seeded-regression/false-proof rate, unverified-gap honesty, intervention count, reproducibility, wall time, calls/tokens and actual/estimated/unknown cost separately. Use development cases, held-out cases and a final untouched audit set. Predeclare acceptance thresholds and the statistical unit before experiments; at least three independent repeats per chosen task is the proposed pilot floor, not a statistically powered general claim. A faithful port can earn value by access/usability even without outperforming Claude. Enhancements must show a relevant benefit without weakening correctness gates.

Research inputs (verified identities, methods still to be read/tested against this task; no transferred performance claims):

- https://arxiv.org/abs/2303.11366 — Reflexion: trial externally grounded repair feedback, not ungrounded self-approval.
- https://arxiv.org/abs/2310.01798 — Large Language Models Cannot Self-Correct Reasoning Yet: reason to test self-critique limits; not a universal statement about future models.
- https://arxiv.org/abs/2407.01502 — AI Agents That Matter: cost, hold-outs and reproducibility discipline.

Private corpus/wiki/foundry/persona collections are optional development inputs, never consumer dependencies or redistributed datasets. Record the exact method, ablation, outcome and limitation in `docs/research-decisions.md`; unsuccessful research stays a rejected candidate. Shared optional evidence adapters must be versioned later without forcing a sibling runtime dependency.

## 8. Planned execution commands and release evidence

These commands are future instructions, NOT results from this planning session. Use an isolated development environment created after BUILD. Keep the three plugins' environments separate. Produce a locked dependency set before treating `uv sync --locked` as executable. If `uv` is unavailable, use a documented equivalent environment; never silently use a live Hermes venv.

```sh
uv sync --locked --extra dev
uv run python -m pytest tests/unit tests/adversarial --strict-markers -ra
uv run python -m pytest tests/integration --strict-markers -ra
uv run python -m pytest tests/host tests/platform --strict-markers -ra
uv run ruff check .
uv run python -m build
hermes plugins validate "$PLUGIN_REPO"
# --install-deps is separately consented in an isolated test host, never a live install by default.
```

Phase 0 must verify the exact target CLI syntax and exit behaviour before placing these in `scripts/checks.sh`. Proposed consumer commands, to be implemented and smoke-tested: `hermes modernise assess --repo <path>`, `plan --job <id>`, `run --job <id>` (requires authentic grant), `status --job <id>`, `compare --job <id>`, `report --job <id> --out <private-path>`, `resume --job <id>`. `modernise_compare` and CLI/slash `compare` only re-derive comparisons from stored, verified execution receipts; they never launch fresh old/new executions. Missing or stale receipts produce a gap; fresh execution uses the separately granted run service. Each CLI/slash/tool maps to the same service method and records surface/caller provenance.

A command exit 0 without collected tests, evidence verification or host coverage is not a release gate. Save exact commands, environment/dependency locks, host SHA/version, native OS/surface, collection counts, skip reasons, failures, benchmark split/seed, actual model attribution/cost completeness, artifact hashes and reviewer verdict. No assertion “all tests passed” without reconciling declared totals.

Release packet: built artifact + checksummed source commit, attribution inventory, compatibility/unsupported table, threat model, runbook, rollback/data-migration instructions, redacted demo + private raw-evidence access policy, independent review and explicit owner INSTALL/DEPLOY/PUBLISH approvals. Soak before deployment where it touches an active service. No public push is authorised by this plan.

## 9. Decisions, blockers and revalidation record

Resolved planning decisions: standalone native plugin; host-neutral core; executable comparison/evidence foundation; no proprietary security adaptation; approvals outside model-written artefacts; no universal proof claim; data survives updates and is never stored under installed code.

Owner choices before BUILD: first real repositories/contracts, language breadth, sandbox backend/privileges, public name/licence, supported host release floor, allowed model egress/budget, acceptable planned behavioural changes. Before INSTALL: native-host matrix and operational scope. Before PUBLISH: actual value comparison, public/private evidence boundary and source/licence audit.

Implementation-blocking spikes: public authority request path and caller identity; verified isolation backend on claimed OS; protected oracle/executor provenance; supported release/ABI floor; actual host route and payload coverage. Until these pass, execution/model egress stays disabled. Their presence is not permission to quietly supply an unsafe fallback.

Plan-source revalidation: parent read the pinned PluginContext signatures, registry dispatch, hook failure policy, storage scope and per-component licences. Rejected a source contribution's uniform-root-Apache assumption. Replaced weak file-text approvals and timestamp/name-only proof with explicit authority/evaluator contracts. Source inspection is verified; reference/runtime/host/benchmark tests have NOT been executed in this planning task. The completed planning-review record is below.

## Final plan revalidation and pickup checklist

Finalisation reference time (actual clock read): 2026-10-14T10:33:34Z. Author: KENSEI. Independent plan reviewer: Quan in isolated contexts. Full semantic/source review: `deleg_626beeb6`; bounded correction recheck: `deleg_522949b9`. These IDs are audit identifiers, not dependencies: the relevant outcomes are captured here so a future agent need not retrieve old chats or scratch transcripts.

- Initial full review: PASS (planning). Baseline authority now precedes legacy execution and is separate from migration/candidate permission.
- Final independent recheck: PASS (planning). Agent `modernise_run` route, journey/state grants and shared-source ledger consistency verified.
- Final nonblocking clarification applied by parent: compare is stored-receipt recomputation only; fresh execution always uses the separately granted run service.

Parent validation actually performed in this task:

- Read pinned native SDK/registry/hook/storage/LLM capability sources and selected reference code/licences; distinguished existing APIs from proposed contracts and unexecuted spikes.
- Checked every immutable A/H blob URL in the final plan against the pinned local source/Git object; corrected erroneous source paths rather than claiming they existed. Verified code-fence balance, complete phase/test sections and unique owned identifiers.
- Rechecked the applied authority/surface/required-check corrections in the documents and verified the files live under Sahil-readable handoff directories. No plugin was built, installed or enabled; no test/benchmark/runtime/sandbox outcome was fabricated.

Final planning verdict: PASS, with owner-gated Phase 0 engineering spikes retained. This is NOT implementation certification, a claim that the public authority route already exists, a demonstrated OS sandbox, or permission to act on a live repository. Future source drift can invalidate assumptions; re-pin and rerun Phase 0 instead of “repairing” identifiers or silently changing the design.

Pickup checklist:

1. Use this document as the standalone specification; all relevant context and primary references are inline. Select one plugin repository/worktree; siblings are neither prerequisites nor writable scope.
2. Confirm owner BUILD approval and the exact disposable test/experiment scope; INSTALL/DEPLOY/PUBLISH and live config/credentials/privileges remain separately gated. Freeze first real cases, host/OS/parser support, budget and egress decisions.
3. Complete the named Phase 0 blockers before enabling dependent execution/capture/live-read/model lanes. Report any failed seam and request a decision; no private API, counterfeit receipt, unsafe fallback or silently weakened acceptance criteria.
4. Execute the task/test traceability table with witnessed RED/GREEN, meaningful collection totals, negative controls, native interfaces and independent implementation review. Save actual commands/results privately and separate public synthetic examples from private factory/benchmark/corpus data.
5. Deliver a working artifact and reproducible evidence, then stop at the owner gate. Planning PASS does not imply BUILD/INSTALL/DEPLOY/PUBLISH approval.


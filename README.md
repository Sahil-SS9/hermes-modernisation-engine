# Modernisation Engine — unreleased engineering preview

This is NOT the finished migration engine and is NOT ready for live installation.

## Active public build — start here

Public repository: https://github.com/Sahil-SS9/hermes-modernisation-engine (branch `build/phase0`). No live installation or deployment is authorised.

- [Resume handoff](docs/HANDOFF.md): state verification, safe commands, local prerequisites and pickup order.
- [Updated plan](docs/PLAN.md): current position plus the original requirements preserved verbatim.
- [Completed work and TODO](docs/TODO.md): checked-off delivered components and every remaining milestone.
- [Development/recovery archive](development/README.md): historical controller sources and probes; not runtime commands.
- [Current source-bound evidence](docs/evidence/remaining-build-20261021/fix-pass-2.json): exact tested source, remediation results and remaining limits. Older checkpoint files are historical, not current totals.

Current isolated remediation gate: 463 passed, zero failures/errors/skips; lint and warning-free native validation pass. The gate was run against the owner-approved rebuilt sandbox image after the exact `a947dae2…` image could not be restored locally. This includes the repairs for the independent review’s two P1 findings and one P2 finding. A configured owned-fixture journey still proves fixture orchestration, not live application execution or release qualification. Points 2–3 remain fixture-bound; point 4 independent review/release remains separate.

Implemented: source-only bounded assessment, lexical Python inventory with exact citations, conservative rule candidates, source fingerprints, durable profile-owned assessment jobs and content-addressed inventory pages, idempotent creation, stale-revision checks, source-replacement proposal validation and separate-candidate materialisation primitives, deterministic data comparison with conservative partial proof policy, review-only plans, explicit missing-evidence JSON/text/offline-HTML reporting, real Hermes CLI/tool/registered-slash-handler surfaces and external owner-signature primitives. An operator-only executor primitive has real synthetic-container tests for success, streaming output cap, timeout/descendant cleanup and replay refusal. Those are fixture-authority controls, not real owner migration acceptance.

The current isolated build also connects separate signed contract/migration review, exact one-use operation grants, protected input-only process collection, engine-reserved candidates, authenticated private observation recomputation and explicit cancellation/runtime/build recovery. Without trusted operator configuration and current exact authority, run still refuses. Resume revalidates completed work only; uncertain work needs explicit signed retirement and a fresh attempt, never blind replay. Current MigrationJob v1 headers are strict and profile/row/contract-bound; sparse legacy assessment records remain readable without being silently upgraded. No operation can manufacture owner approval.

Still open: complete rule/execution/comparison/report schemas and state/profile/concurrency acceptance; broader upgrade/dependency-resolution/framework/module adapters; optional model orchestration, real budgets and batches; signed narrow differences, rule adequacy/mutation-qualified proof; full native/gateway execution and supported-release/platform qualification. Zero/disabled budget metadata is not a working model-budget lane. No full-engine completion, whole-system equivalence or independent release acceptance is claimed.

## Standalone source assessment

    python -m hermes_modernisation --data-dir /absolute/private/job-data assess --repo /absolute/source-copy --goal "Upgrade Python" --request-id request-001
    python -m hermes_modernisation --data-dir /absolute/private/job-data inventory --job <id> --section symbols --page 0
    python -m hermes_modernisation --data-dir /absolute/private/job-data plan --job <id> --revision 0
    python -m hermes_modernisation --data-dir /absolute/private/job-data status --job <id>
    python -m hermes_modernisation --data-dir /absolute/private/job-data compare --job <id>
    python -m hermes_modernisation --data-dir /absolute/private/job-data report --job <id>

Assessment never imports/executes repository code, resolves package installations or calls a model. It writes only private job metadata, not source files. Repo instructions are data, not approval. Configured data roots must be owner-only and outside source/candidate roots. JSON size/depth/type/path limits fail closed. Existing source symlinks, hardlinks, special files and recognised credential filenames are refused. Known generated directories are explicitly excluded; this is not proof of dependency/environment completeness. AST extraction does not find all business rules or resolve dynamic calls.

## Hermes directory plugin

Distribution is `plugin.yaml` plus root `__init__.py`. The Python wheel provides the standalone core/CLI only; it does NOT also register a Hermes plugin entrypoint. Use the complete directory artifact for Hermes. Never install both competing discovery registrations.

Hermes commands include `assess`, `inventory`, `plan`, `status`, `contract`, `schema`, `review_request`, `review`, `prepare`, `attempts`, `proposal`, `build`, `run`, `resume`, `control_request`, `cancel`, `recover`, `recover_build`, `record`, `protocol`, `response_protocol`, `recipe`, `compare` and `report` under `hermes modernise`. Equivalent tool names have the `modernise_` prefix. The registered `/modernise` handler uses the same service, but full gateway and interactive slash dispatch acceptance is outstanding. Job metadata resolves under the active profile's `plugin-data/modernisation-engine/private` on each call.

Sandbox host compatibility is proven only on PR #138686 head `4539b09a730d6a97548b4d4102d10990033ead36` PLUS the separately identified local validator handle patch. Neither fix is claimed merged or installed. Public version metadata is insufficient to establish that floor. See `docs/validator-compatibility-repair.md` and the current development checkpoint.

## Development boundaries

All untrusted repository-code workloads and package-build workloads run in disposable, resource-limited, network-disabled rootless containers. The trusted external operator control plane runs on the host to control rootless Docker; it is never mounted into a candidate. Image preparation alone may retrieve pinned development dependencies. No real credentials, host home or Docker socket are mounted. Source and engine references remain read-only; build output is extracted from disposable storage by the trusted operator. Docker shares the host kernel; this is not a VM, and a compromised trusted host/operator is outside the claim.

The engine is a public, unreleased engineering preview; the external host validator patch has not been taken up live or claimed merged upstream. No live install, deployment, telemetry or scheduled auto-rewrite is authorised. BUILD/INSTALL/DEPLOY are separate owner approvals. No supported-release promise is made by this preview.

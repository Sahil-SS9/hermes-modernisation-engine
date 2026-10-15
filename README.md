# Modernisation Engine — unreleased engineering preview

This is NOT the finished migration engine and is NOT ready for live installation.

## Parked checkpoint — start here

Private backup: https://github.com/Sahil-SS9/hermes-modernisation-engine (branch `build/phase0`). No live installation or public release is authorised.

- [Resume handoff](docs/HANDOFF.md): state verification, safe commands, local prerequisites and pickup order.
- [Updated plan](docs/PLAN.md): current position plus the original requirements preserved verbatim.
- [Completed work and TODO](docs/TODO.md): checked-off delivered components and every remaining milestone.
- [Evidence checkpoint](docs/evidence/checkpoint-2026-10-15.json): producing code, verified scopes and recovery fingerprints.

The implementation baseline is `b914c6d118584a45736611c93bb772905108acd6`. Current preview tests: 108 passed, zero failures/errors/skips; lint and native validation passed on the explicitly patched sandbox host. This is not full-engine or independent-release acceptance. Fresh exact owner signatures are required for the real regression runs; other prerequisite coding tasks can proceed independently when resumed.

Implemented: source-only bounded assessment, lexical Python inventory with exact citations, conservative rule candidates, source fingerprints, durable profile-owned assessment jobs and content-addressed inventory pages, idempotent creation, stale-revision checks, source-replacement proposal validation and separate-candidate materialisation primitives, deterministic data comparison with conservative partial proof policy, review-only plans, explicit missing-evidence JSON/text/offline-HTML reporting, real Hermes CLI/tool/registered-slash-handler surfaces and external owner-signature primitives. An operator-only executor primitive has real synthetic-container tests for success, streaming output cap, timeout/descendant cleanup and replay refusal. Those are fixture-authority controls, not real owner migration acceptance.

Not implemented/enabled: general baseline/candidate executor, patch/model orchestration, protected oracle lifecycle, authenticated receipt ingestion, behavioural equivalence proof, complete MigrationJob schema/state/fencing, owner-approved normalisation/tolerances, framework/module migration fixtures, benchmark/value experiments, independent implementation review and release gates. `run` and `resume` refuse; no command can manufacture approval. The signed baseline in private development evidence is a separately scoped external-adapter demonstration, not a claim that this package contains that complete execution service.

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

Hermes commands: `hermes modernise assess|plan|status|compare|report`. Equivalent tool names have the `modernise_` prefix. The registered `/modernise` handler uses the same service, but full gateway and interactive slash dispatch acceptance is outstanding. Job metadata resolves under the active profile's `plugin-data/modernisation-engine/private` on each call.

Sandbox host compatibility is proven only on PR #138686 head `4539b09a730d6a97548b4d4102d10990033ead36` PLUS the separately identified local validator handle patch. Neither fix is claimed merged or installed. Public version metadata is insufficient to establish that floor. See `docs/validator-compatibility-repair.md` and the current development checkpoint.

## Development boundaries

All untrusted repository-code workloads and package-build workloads run in disposable, resource-limited, network-disabled rootless containers. The trusted external operator control plane runs on the host to control rootless Docker; it is never mounted into a candidate. Image preparation alone may retrieve pinned development dependencies. No real credentials, host home or Docker socket are mounted. Source and engine references remain read-only; build output is extracted from disposable storage by the trusted operator. Docker shares the host kernel; this is not a VM, and a compromised trusted host/operator is outside the claim.

The engine and external host validator patch are local-only. No merge, public push, live install, deployment, telemetry or scheduled auto-rewrite. BUILD/INSTALL/DEPLOY/PUBLISH are separate owner approvals. No public licence or supported release promise is made by this unreleased preview.

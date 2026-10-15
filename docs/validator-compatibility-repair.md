# Validator recording-handle compatibility repair

Status: fixed and verified LOCALLY IN SANDBOX ONLY. Not an upstream fix, PR update, live install, full engine completion or release acceptance.

Sahil authorised direct implementation of the next steps. No delegation, public write, live repo/config/credential change or deployment performed.

## Exact boundary

Unchanged base host: PR #138686 commit `4539b09a730d6a97548b4d4102d10990033ead36`, accepted sandbox image `modernise-pr138686@sha256:6dc445d00c009cf4fad014a40a2c97952230a17142460bd04df367c4061cae02`.

One core file was independently copied and patched OUTSIDE existing host repositories:
`/home/kensei/projects/modernisation-benchmarks/control/validator-fix/plugin_validate.py`.

Fixed image: `modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6`.

This is the PR host plus a separately authored local validator patch, not the unmodified PR or current public upstream. The plugin's register/collision/authority code was NOT weakened or changed for the fix.

## Cause and repair

The validator executes register() with a recording-only context. Its register_tool/register_command/register_cli_command methods appended names but returned None. Real successful registration returns a lifecycle handle; a foreign CLI collision returns None. The plugin correctly refuses None, so the recording probe falsely rejected valid plugins that check successful registration handles.

The local patch returns a PROBE-LOCAL handle from those three explicitly modelled methods. It supports active and idempotent dispose; disposal removes only its own identity from recorded capabilities, even when another registration has the same name. It imports no host registry, credentials or approval policy. It cannot mint an execution grant or register live tools. Unknown recording surfaces retain their prior behaviour; the patch is not a promise of complete PluginContext emulation.

Two regression tests were written and run before the repair: public `hermes plugins validate /source --json` failed with the actual false collision; the recording lease/disposal regression failed on None. Both pass with the patched image. Additional assertions cover duplicate-name lease identity and absence of core-plugin imports inside the recording child.

## Observed results

- All 35 current engine tests pass under Python 3.14.8/pytest 9.1.1 in the fixed rootless container. Exact totals are extracted from JUnit: 35 tests, 0 failures/errors/skips.
- All current engine src/tests/scripts/root entrypoint pass Ruff.
- Actual public `hermes plugins validate /source --json` exits 0, reports ok=true, successful capability probe, declared tools/hooks/middleware matching, safe scan, no core override.
- Original unchanged native CLI collision repro still passes 2/2.
- Extended 11-file upstream SDK/validator/lifecycle regression set passes 194/194, 0 failures/errors/skips. This includes the earlier 160-file-selection test CASES (not 160 distinct files) plus 34 validator/private-import/locale cases. Counts are not additive across overlapping runs.
- Upstream-focused run retains 21 warnings: 20 deprecations and the previously disclosed logging-thread/home-I/O-guard warning inside disposable /tmp/hermes. No claim that every warning is harmless or that the full host suite is green. The warning did not newly appear with this patch; full causal attribution is not performed.

Runtime tests use network none, read-only image/source, no Docker socket or host credentials/home, uid 65534, process/memory/CPU limits and disposable tmpfs. Host recipes require dependency retrieval only during image preparation; the validator overlay itself contains no RUN and was built with network=none. A first FROM-by-local-digest lookup failed because BuildKit tried the remote registry; the local tag was then verified against the exact parent image SHA and BuildKit recorded that same digest as its resolved parent. No public image was pushed.

Private command/exit/JUnit-count/checksum/cleanup evidence:
`/home/kensei/projects/modernisation-benchmarks/control/evidence/validator-fixed-engine-{owned,lint,validate}.{json,log}` and `validator-fixed-host-{original-probe,focused}.{json,log}`.

Reproduction wrappers:
`/home/kensei/projects/modernisation-benchmarks/control/check-engine-validator-fixed.py`
`/home/kensei/projects/modernisation-benchmarks/control/verify-validator-fixed-host.py`

Earlier red logs and earlier host/validator reports remain historical evidence, not current acceptance status. The local validator patch must be reviewed and separately approved for upstream submission if desired; no public contribution is authorised by this task.

## Where the product stands

The original CLI blocker and the validator mismatch are closed for this EXACT sandbox host. The engine is still a Phase 0 preview with real load/status/denial/lifecycle surfaces, NOT a migration implementation.

Remaining declared work: full native caller/authority and lifecycle/timeout/profile acceptance; executor process-tree/output/time/recovery checks; M0.4 licence/prior-art/reference-conformance ledger; then M1 strict versioned contracts, M2 durable jobs, M3 inventory/rules, M4 trusted runner, M5 comparison/proof, M6 proposals, M7 reports/end-to-end, M8 platform/host matrix and M9 review/value/release packet. Build/INSTALL/DEPLOY/PUBLISH remain separate. Original walkie-talkie and its isolated clone remain clean and unchanged; Python 3.14 plus FastAPI migration remains unperformed.

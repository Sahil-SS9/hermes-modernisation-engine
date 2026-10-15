# PR host take-up and native plugin checkpoint

Status: original CLI collision blocker CLOSED for sandbox development on PR #138686 head `4539b09a730d6a97548b4d4102d10990033ead36`; full engine remains PARTIAL. No live/public changes.

## Approval and exact host

Sahil approved direct sandbox verification of the PR and continued engine development. No delegation, live installation, public write, merge or deployment is approved. The prior Python 3.14 + FastAPI candidate migration scope remains approved, but the benchmark itself remains unchanged.

PR metadata was read fresh: OPEN, head `4539b09a730d6a97548b4d4102d10990033ead36`, no reported CI checks. Upstream merge/CI status is separate from local compatibility acceptance.

Exact GitHub archive SHA-256: `55b09f16851287d8655d7038db743dad6de435d1a4d7e05aec9b5002a7515f7b`. Archive staged outside all active repositories at `/home/kensei/projects/modernisation-benchmarks/control/pr138686/host-src`. This is a source archive, not a Git checkout; do not attribute an ancestor directory's Git HEAD to it.

Sandbox host image: `modernise-pr138686@sha256:6dc445d00c009cf4fad014a40a2c97952230a17142460bd04df367c4061cae02`.
Python 3.14.8. Actual committed host lock installed with `uv sync --locked --group dev --group test`, pytest 9.1.1. Image embeds `/host-dependency-manifest.txt`. No live venv changed. Build dependency network was confined to image preparation with source archive only; all tests used network none, read-only source/root, no credentials/socket/live home, unprivileged uid, resource caps and init.

## Independently rerun here (no delegated claims)

- Original UNMODIFIED external native CLI collision probe: 2 collected, 2 passed, zero failures/errors/skips. The installed `hermes` executable resolves the original observed failure.
- Exact eight-file focused SDK suite: 160 collected, 160 passed, zero failures/errors/skips, counts parsed from JUnit testcase records. Existing lifecycle/concurrency/same-owner/disposal tests included.
- Focused SDK suite emitted 18 warnings: 17 deprecations plus one pytest unhandled logging-thread warning. The latter concerns host test home-I/O guard activity against disposable `/tmp/hermes/logs/agent.log`. Not a live-home write: no host home is mounted. It remains a disclosed suite-hygiene limitation; not silently counted as a passing thread assertion, not independently baseline-attributed, not a reason to keep the closed CLI defect open.
- No full upstream suite or native macOS/Windows certification is claimed. CI remains unavailable/pending.

Private evidence: `/home/kensei/projects/modernisation-benchmarks/control/evidence/pr138686-original-probe.{json,log}` and `pr138686-focused.{json,log}`. Actual commands, exact image/source identities, output hashes, JUnit counts and container removal observations are retained. Wrapper: `/home/kensei/projects/modernisation-benchmarks/control/verify-pr138686.py`.

## Continued implementation

Added native directory plugin manifest/entrypoint and a thin Hermes adapter. It registers only a read-only status tool plus CLI/slash status; execution remains refused because downstream executor acceptance is incomplete. No fabricated assess/plan/compare/report output or approval endpoint is exposed.

Added real host tests for temporary-home discovery, installed CLI status and run denial, actual tool registry dispatch, registered slash handler, force reload and unload cleanup. Registered slash handler coverage is NOT a full interactive slash/gateway dispatch claim. Status explicitly reports PHASE_0_ONLY and missing evidence. Native host tests passed 4/4 (including original two-owner regression) on the PR image. Initial loader tests failed because the plugin manifest did not exist; that is artifact-presence RED, not a valid witnessed production behavioural RED claim. Runtime assertions after implementation supply real-seam coverage.

The public run surface cannot be enabled from `--approved`, tool arguments or model text. Native CLI namespace collision causes registration refusal and already-created handles are disposed.

Whole owned suite on the accepted PR host: 33 collected, 33 passed, zero failures/errors/skips; full current src/tests/scripts/entrypoint Ruff check passed. An initial combined runner explicitly injected HERMES_HOME, conflicting with the existing no-inherited-home assertion. The operator runner was corrected to omit that variable; the safety test was NOT weakened. Initial red output is retained as `accepted-pr138686-engine-owned-initial-env-failure.*`.

`hermes plugins validate /source --json` is still RED: its capability-probe RecordingContext returns None for every successful registration, while the real public SDK uses None for a collision refusal. The plugin correctly refuses that ambiguous outcome. Its manifest, security scan, no-core-override and real loader/CLI/registry/lifecycle tests pass, but this synthetic validator cannot certify the candidate. Source: pinned PR `hermes_cli/plugin_validate.py:213–231`. Do not special-case the probe's plugin ID, weaken collision handling or call the validator green. A supported recording-handle contract/validator correction or owner-approved packaging decision remains a separate release acceptance item. This does not reopen the original PR collision defect or claim full M0.1 completion.

Remaining full lifecycle/foreign-owner rollback, settings/profile scope, loader deadlines, gateway/caller authentication, executor/output-time/process-tree acceptance, licence/prior-art/conformance, protected oracle and M1–M9 gates remain open.

Original pinned H observations and original failed tests remain historical evidence; do not overwrite or label them fixed upstream. Current sandbox development has deliberately advanced to the reviewed PR head, not to a modified live installation.

# Compatibility and operator runbook

Engineering preview only. No supported public release or install instruction is authorised.

## Verified floor, not a guessed version range

The only native-host evidence is Linux on Hermes PR #138686 head `4539b09a730d6a97548b4d4102d10990033ead36` plus local validator recording-handle repair image `modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6`. Python 3.14.8, pytest 9.1.1, Ruff 0.15.10, cryptography 50.0.1 and setuptools 83.0.0 were observed inside that image. ABI/version labels alone do not prove either repair. No claim that PR changes merged upstream. `requires_hermes` remains undeclared pending an actual released host floor; README status explicitly warns this is not installation-ready.

Native tested: fresh directory-plugin installation in a disposable profile, real CLI status/assess/inventory/plan/compare/report, actual tool registry dispatch, registered slash-handler parsing, force reload and cleanup of every declared tool on unload; foreign CLI registration collision refusal. These are not full interactive TUI or gateway slash-dispatch tests. There is no dashboard/UI surface. Windows/macOS execution is unsupported; source-read/report portability there is unverified. Python 3.11–3.13 consumer runtime support is declared packaging intent, NOT an executed test matrix.

All source assessment/parser/reference/consumer-build workloads run in rootless network-disabled containers with read-only bind sources. The external operator executor control plane runs locally, not inside a candidate and not through raw model tool dispatch. It has no fallback from missing Docker, missing cryptography, owner signature refusal, rootless failure or cleanup uncertainty. Use a dedicated operator venv with pinned verification dependencies, not the live Hermes environment.

## Data and recovery

Current preview tables are assessment jobs and content-addressed inventory pages. Source snapshots use identity schema v2 (file bytes/modes and nonexcluded directory paths/modes), while grant envelopes remain operation schema v1 and bind the actual identity digest. Preserve older digests as historical evidence; never reinterpret old signatures as approving a new source-identity algorithm.

Status/compare/report/inventory use SQLite mode=ro; missing stores refuse without creating metadata. Assessment/plan use transactionally private v2 stores; idempotency-key changes and stale revisions refuse. An explicit write/Store.migrate upgrades a v1 store only after a consistent private `jobs.pre-v2.sqlite` backup. Reads can still read old job bodies. Restore requires closing every reader/writer and owner-approved replacement from the backup; no automatic destructive downgrade or overwrite is offered. An existing backup during interrupted migration blocks for inspection, not silent deletion. Test downgrade/restore across a full deployed host is still outstanding.

Never delete plugin-data on uninstall/reinstall; no uninstall hook exists. No source/user-repo removal or Git push/merge occurs. Do not mistake removal of disposable execution containers for a source cleanup request.

An external-executor attempt has immutable attempt/container descriptors, frozen sources, raw bounded `output.bin` and, after collection/verified cleanup, a process-only receipt. On operator crash: first inspect exact persisted container name/ID; if execution state is ambiguous, keep the attempt INTERRUPTED and obtain a fresh exact owner grant for a new attempt only after manual recovery. Never replay a consumed nonce, automatically reattach to a guessed process, erase failed evidence or treat old stdout as a fresh process result. The active build has a fenced attempt journal, configured exact-grant run and completed-only resume, plus protected Engine-owned fixture capture. Explicit cancellation/retirement and exhaustive crash recovery remain incomplete; uncertain attempts refuse replay. Full native/gateway execution acceptance remains open and live execution is unconfigured. See the current `configured-capture.json` source-bound checkpoint; this does not amend unsupported-platform or release claims.

## Private evidence vs consumer artifact

Private raw logs, source inventory pages, baseline/candidate source, owner grant material and evaluator labels belong under the controlled handoff/control directories, not in a public release artifact. Directory preview includes only consumer src, manifest/entrypoint, metadata/lock, README and selected generic docs. Python wheel is standalone core/CLI only. The development reference cache is read-only and not redistributed; its Apache licence is not a licence for this engine.

Build artifact extraction verifies actual bytes/SHA-256. Wheel install smoke runs offline in a fresh disposable venv, imports with source PYTHONPATH removed, performs assess/status and confirms unauthorised execution refusal. tmpfs is noexec: module CLI execution through the known interpreter is exercised; direct console-script exec on an executable consumer filesystem remains unverified. The offline directory archive is validated again through the native loader/checker before claiming usable plugin packaging.

BUILD is not INSTALL, DEPLOY or PUBLISH. Independent implementation review, real-project oracle acceptance, model-egress/budget decisions and complete phase/test matrix remain explicit blockers to claiming the whole engine complete.

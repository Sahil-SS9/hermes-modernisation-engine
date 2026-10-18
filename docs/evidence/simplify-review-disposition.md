# Simplify-swarm disposition — controller judgement, round 1

Scope: HEAD 14abbb0c092dc1c58963f19e2939a4892b29dd6d plus returned dirty source. Three read-only Quan roles reviewed the source before remediation; the controller independently reproduced the initial 164-test suite and added four failing behavioural regressions. This review is not full independent engineering acceptance.

Original role returns remain in `/home/kensei/.hermes/cache/delegation/live/deleg_e2c805c9/task-{0,1,2}.log`. No source was modified while the roles read it. The controller added only its separate regression file and evidence sidecar.

## Accepted functional findings

- Old-schema compare/report regression: controller reproduced both schema 1 and 2 failures. Fix read-only compatibility; do not migrate on read or silently treat a malformed current-schema database as an old store.
- FIFO retained-output hang: controller reproduced the public record operation blocking before fstat. Use the existing nonblocking no-follow file-read pattern and retain regular-file, single-link and size validation.
- Comment-only recipe preimage: controller reproduced an accepted candidate whose real dashboard pin was unsupported. Validate actual parsed TOML fields, not comments or token presence.
- Cross-phase expectation mismatch: source-supported and not covered by the implementer's misleading pairing test (that test actually rejects output/expectation mismatch). Before editing, add a genuinely matching second-phase output under a different expectation and witness refusal failure. Refuse mismatched pairing within the same write transaction, without reserving the phase or losing already-valid evidence.
- Incomplete residue-marker window: source-supported. Before editing, exercise a post-copy freshness/refusal failure as well as mid-copy failure. Every failure after destination creation must retain its provenance; preserve residue and refuse reuse, never auto-delete it.

Controller RED receipt: `control/evidence/development-unit-1792359326101694119.json` (140 passed, four failed, zero errors/skips), through the existing isolated runner. The original implementation report is preserved; see `controller-review-round1.md`.

## Rejected or non-blocking recommendations

- Do NOT auto-delete or replace an interrupted migration backup. The existing compatibility/threat-model contract deliberately preserves failed/colliding backups and refuses a write until operator inspection. The review's automatic deletion/replace suggestion conflicts with that rule. Improve clarity only if required; preserve evidence and the refusal contract.
- The claimed 5000-by-600-character legal expectation is not established: the strict JSON input/evaluation byte limits must be checked before asserting that it reaches persistence. Do not loosen JSON limits or add a guessed worst-case formula. A concrete supported-size failure can be investigated separately; a conservative explicit refusal is not false proof or partial storage.
- Drop gratuitous import moves, alias renames and comment churn. No independent simplify application was authorised; the source review was analysis-only. Address meaningful duplication only when required by the bounded functional repair (for example strict argument decoding or verified preimage flow), preserving public error transports.
- A shared argument/operation schema must not remove service-side validation. Do not introduce a framework solely to remove a few duplicated flags.

## Completion gaps retained as engineering, not owner-signing blockers

The partial recipe still omits uv.lock and the already-tested pytest-asyncio/Starlette follow-up; caller-declared candidate digests are not a stored staging/job binding; imported JUnit remains unauthenticated and candidate-authored. These facts are honestly documented but do not meet the requested complete upgrade/checking outcome. Complete the narrow offline metadata/staging path rather than renaming a partial candidate as ready. Independent capture needs a concrete protected channel and acceptance contract; do not claim it from a digest or a parser.

All release/live/real-code execution holds remain. Parent will run fresh isolated checks and a separate adversarial review after the bounded corrections. No PASS, commit, push or deployment is granted by this record.

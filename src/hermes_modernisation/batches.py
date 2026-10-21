"""Bounded, typed proposal batches with an injected proposer port.

The engine never reaches a provider or reads provider credentials here.  A
trusted composition root may inject either the offline fixture port (tests and
declared offline runs) or ``HermesPublicModelAdapter`` with an explicit
``complete`` callable supplied by its caller.  Model output is data only:
literal replacement text inside the declared path scope, never a command,
tool call, dependency edit or authority claim.
"""

import hashlib
import queue
import threading
import time
from pathlib import Path

from .identity import read_source, safe_relative, snapshot
from .jsonio import ContractError, dumps, identifier, loads
from .proposals import validate_proposal

BUDGET_FIELDS = {
    "max_calls",
    "max_input_bytes",
    "max_output_bytes",
    "max_seconds",
    "max_tokens",
}
BATCH_FIELDS = {"batch_id", "paths", "instruction"}
ENVELOPE_FIELDS = {"text", "usage"}
USAGE_FIELDS = {"input_tokens", "output_tokens"}
RESPONSE_FIELDS = {"schema_version", "batch_id", "changes"}
CHANGE_FIELDS = {"path", "replacement"}
MAX_FILE_BYTES = 65536
MAX_REPLACEMENT_BYTES = 262144


class BatchRefused(ContractError):
    """A batch stopped for a named, non-authorising reason."""

    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code


class ProposalOutage(BatchRefused):
    def __init__(self, message):
        super().__init__("PROPOSER_OUTAGE", message)


def _bounded_integer(value, minimum, maximum, label):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError(f"Bounded integer {label} required")
    return value


def validate_budget(value):
    if type(value) is not dict or set(value) != BUDGET_FIELDS:
        raise ContractError("Unsupported proposal budget fields")
    _bounded_integer(value["max_calls"], 1, 16, "call cap")
    _bounded_integer(value["max_input_bytes"], 1, 1048576, "input byte cap")
    _bounded_integer(value["max_output_bytes"], 1, 1048576, "output byte cap")
    _bounded_integer(value["max_seconds"], 1, 300, "time cap")
    _bounded_integer(value["max_tokens"], 1, 200000, "token cap")
    return value


def validate_batches(value, allowed_paths):
    if type(value) is not list or not 1 <= len(value) <= 8:
        raise ContractError("Bounded proposal batches required")
    identifiers = set()
    paths = set()
    for batch in value:
        if type(batch) is not dict or set(batch) != BATCH_FIELDS:
            raise ContractError("Unsupported proposal batch fields")
        identifier(batch["batch_id"])
        if batch["batch_id"] in identifiers:
            raise ContractError("Duplicate proposal batch identity")
        identifiers.add(batch["batch_id"])
        declared = batch["paths"]
        if type(declared) is not list or not 1 <= len(declared) <= 20:
            raise ContractError("Bounded distinct batch paths required")
        for item in declared:
            path = safe_relative(item)
            if path in paths:
                raise ContractError("Overlapping proposal batches refused")
            if path not in allowed_paths:
                raise ContractError("Batch path is outside the reviewed scope")
            paths.add(path)
        if (
            type(batch["instruction"]) is not str
            or not 1 <= len(batch["instruction"]) <= 2000
            or "\0" in batch["instruction"]
        ):
            raise ContractError("Bounded batch instruction required")
    if len(paths) > 100:
        raise ContractError("Proposal path limit exceeded")
    return value


def _envelope(value):
    if type(value) is not dict or set(value) != ENVELOPE_FIELDS:
        raise BatchRefused(
            "INVALID_RESPONSE",
            "proposer must return exactly text and usage; tool calls/extra fields are refused",
        )
    usage = value["usage"]
    if type(usage) is not dict or set(usage) != USAGE_FIELDS:
        raise BatchRefused("INVALID_RESPONSE", "exact token usage required")
    for key in USAGE_FIELDS:
        _bounded_integer(usage[key], 0, 200000, f"usage {key}")
    if type(value["text"]) is not str or not value["text"]:
        raise BatchRefused("INVALID_RESPONSE", "non-empty response text required")
    if any(marker in value["text"] for marker in ("```", "<tool", "tool_calls")):
        raise BatchRefused(
            "INVALID_RESPONSE", "markdown fences/prose tool instructions are refused"
        )
    return value


def _batch_text(batch, text, declared):
    try:
        value = loads(text)
    except ContractError as error:
        raise BatchRefused("INVALID_RESPONSE", "response is not exact JSON") from error
    if type(value) is not dict or set(value) != RESPONSE_FIELDS:
        raise BatchRefused("INVALID_RESPONSE", "exact typed batch response required")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise BatchRefused("INVALID_RESPONSE", "unsupported batch response version")
    if value["batch_id"] != batch["batch_id"]:
        raise BatchRefused("INVALID_RESPONSE", "response batch identity differs")
    changes = value["changes"]
    if type(changes) is not list or not 1 <= len(changes) <= 20:
        raise BatchRefused("EMPTY_BATCH", "every batch needs bounded literal changes")
    seen = set()
    cleaned = []
    for change in changes:
        if type(change) is not dict or set(change) != CHANGE_FIELDS:
            raise BatchRefused("INVALID_RESPONSE", "unsupported change fields")
        path = safe_relative(change["path"])
        if path not in declared or path in seen:
            raise BatchRefused("INVALID_RESPONSE", "change path is outside its batch")
        replacement = change["replacement"]
        if type(replacement) is not str or not replacement or "\0" in replacement:
            raise BatchRefused("INVALID_RESPONSE", "non-empty literal replacement required")
        if len(replacement.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
            raise BatchRefused("BUDGET_EXCEEDED", "replacement byte limit exceeded")
        seen.add(path)
        cleaned.append({"path": path, "replacement": replacement})
    if seen != set(declared):
        raise BatchRefused("INVALID_RESPONSE", "every declared batch path needs one change")
    return cleaned


def _prompt(job, batch, contents):
    return dumps(
        {
            "schema_version": 1,
            "task": "literal-source-replacement",
            "goal": job["goal"],
            "batch_id": batch["batch_id"],
            "instruction": batch["instruction"],
            "files": [
                {"path": path, "content": text} for path, text in contents
            ],
            "rules": [
                "Return one exact JSON object: {\"schema_version\":1,\"batch_id\":...,\"changes\":[{\"path\":...,\"replacement\":...}]}.",
                "Replace every declared path exactly once with complete literal UTF-8 text.",
                "No tools, commands, installs, dependency/build edits, tests, or prose.",
            ],
        }
    )


def _propose_with_deadline(proposer, prompt, deadline):
    """Call an injected port, but stop waiting at the total-run deadline.

    The port is arbitrary third-party code and may block indefinitely.  A
    daemon worker lets the engine refuse at its deadline even when that code
    has no cancellation API.  A worker that returns after the deadline is
    never accepted; its result is discarded with the timed-out queue.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise BatchRefused("BUDGET_EXCEEDED", "time cap reached before the next call")
    results = queue.Queue(maxsize=1)

    def invoke():
        try:
            results.put((True, proposer.propose(prompt)))
        except BaseException as error:  # re-raise in the caller's thread
            results.put((False, error))

    worker = threading.Thread(target=invoke, name="proposal-call", daemon=True)
    worker.start()
    try:
        ok, value = results.get(timeout=remaining)
    except queue.Empty:
        raise BatchRefused("BUDGET_EXCEEDED", "time cap exceeded") from None
    if not ok:
        raise value
    return value


def propose(job, contract, batches_value, budget_value, proposer):
    """Run bounded batches and return a validated proposal, never saved here."""
    budget = validate_budget(budget_value)
    batches = validate_batches(batches_value, set(contract["allowed_paths"]))
    if len(batches) > budget["max_calls"]:
        raise BatchRefused("BUDGET_EXCEEDED", "batch count exceeds the call cap")
    if type(job) is not dict or type(job.get("repo")) is not str:
        raise ContractError("Current migration job required")
    source = Path(job["repo"])
    manifest = snapshot(source)
    if manifest["digest"] != job["assessment"]["source_digest"]:
        raise ContractError("Source changed; proposal batches are stale")
    started = time.monotonic()
    input_bytes = 0
    output_bytes = 0
    tokens = 0
    calls = 0
    summaries = []
    by_path = {}
    for batch in batches:
        if tokens >= budget["max_tokens"]:
            raise BatchRefused("BUDGET_EXCEEDED", "token cap reached before the next call")
        if time.monotonic() - started > budget["max_seconds"]:
            raise BatchRefused("BUDGET_EXCEEDED", "time cap reached before the next call")
        contents = []
        for path in batch["paths"]:
            raw, _ = read_source(source, path)
            if len(raw) > MAX_FILE_BYTES or b"\0" in raw:
                raise BatchRefused("UNSUPPORTED_INPUT", "batch input is binary or oversized")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise BatchRefused("UNSUPPORTED_INPUT", "batch input is not UTF-8") from error
            contents.append((path, text))
        prompt = _prompt(job, batch, contents)
        encoded = prompt
        input_bytes += len(encoded)
        if input_bytes > budget["max_input_bytes"]:
            raise BatchRefused("BUDGET_EXCEEDED", "input byte cap exceeded")
        calls += 1
        try:
            response = _propose_with_deadline(
                proposer, prompt, started + budget["max_seconds"]
            )
        except BatchRefused:
            raise
        except Exception as error:
            raise ProposalOutage(f"proposer failed on batch {batch['batch_id']}") from error
        envelope = _envelope(response)
        size = len(envelope["text"].encode("utf-8"))
        output_bytes += size
        if output_bytes > budget["max_output_bytes"]:
            raise BatchRefused("BUDGET_EXCEEDED", "output byte cap exceeded")
        tokens += envelope["usage"]["input_tokens"] + envelope["usage"]["output_tokens"]
        if tokens > budget["max_tokens"]:
            raise BatchRefused("BUDGET_EXCEEDED", "token cap exceeded")
        if time.monotonic() - started > budget["max_seconds"]:
            raise BatchRefused("BUDGET_EXCEEDED", "time cap exceeded")
        for change in _batch_text(batch, envelope["text"], set(batch["paths"])):
            by_path[change["path"]] = change["replacement"]
        summaries.append(
            {
                "batch_id": batch["batch_id"],
                "paths": list(batch["paths"]),
                "output_bytes": size,
                "tokens": envelope["usage"]["input_tokens"] + envelope["usage"]["output_tokens"],
            }
        )
    if len(by_path) != sum(len(batch["paths"]) for batch in batches):
        raise BatchRefused("CONFLICT", "batches did not produce one change per declared path")
    changes = []
    for path in sorted(by_path):
        raw, _ = read_source(source, path)
        changes.append(
            {
                "path": path,
                "before_sha256": hashlib.sha256(raw).hexdigest(),
                "replacement": by_path[path],
            }
        )
    proposal = {
        "schema_version": 1,
        "source_digest": manifest["digest"],
        "goal": job["goal"],
        "changes": changes,
        "allowed_paths": sorted(by_path),
        "planned_differences": [],
    }
    value, _ = validate_proposal(source, proposal)
    digest = hashlib.sha256(dumps(value)).hexdigest()
    return {
        "schema_version": 1,
        "kind": "ProposalBatchResult",
        "job_id": job["job_id"],
        "proposal": value,
        "proposal_digest": digest,
        "batches": summaries,
        "model_calls": calls,
        "input_bytes": input_bytes,
        "output_bytes": output_bytes,
        "tokens": tokens,
        "provider_access": "injected-proposer-only",
        "live_model_call": False,
        "execution_performed": False,
        "verdict": "NOT_PROVEN",
    }


class FixtureProposer:
    """Declared offline fixture: exact responses per batch, optional outage."""

    def __init__(self, responses, *, fail_on=None):
        self._responses = dict(responses)
        self._fail_on = fail_on
        self.prompts = []

    def propose(self, prompt):
        value = loads(prompt)
        batch_id = value["batch_id"]
        self.prompts.append(prompt)
        if batch_id == self._fail_on:
            raise TimeoutError("declared offline proposer outage")
        if batch_id not in self._responses:
            raise KeyError(f"no declared fixture response for {batch_id}")
        return self._responses[batch_id]


class HermesPublicModelAdapter:
    """Adapter over an injected public model callable; no provider/env access."""

    def __init__(self, complete, *, model_id):
        if not callable(complete):
            raise ContractError("An explicit model completion callable is required")
        if type(model_id) is not str or not 1 <= len(model_id) <= 200:
            raise ContractError("Explicit model identity required")
        self._complete = complete
        self.model_id = model_id

    def propose(self, prompt):
        return _envelope(self._complete(prompt))

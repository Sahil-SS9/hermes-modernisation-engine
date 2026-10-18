"""Operator-side evidence ingestion: retained run output -> sealed evaluation.

This is the trusted-host half of the junit-stdout-v1 chain. It never executes
repository code and never treats caller text as proof: the retained output is
evaluated by evaluator.evaluate_output against a predeclared expectation, and
only an ACCEPTED result is persisted, paired with the job, phase, declared
source identity and expectation digest. compare/report verify the stored bytes
again on every read. Everything recorded keeps grade
"candidate-authored-per-case-junit" and proof NOT_PROVEN.
"""

import base64
import hashlib
import os
import re
import stat
from pathlib import Path

from .evaluator import GRADE, MAX_OUTPUT_BYTES, evaluate_output, load_expectation
from .identity import snapshot
from .jsonio import ContractError, dumps
from .store import identifier

PHASES = ("baseline", "candidate")
SOURCE_DIGEST = re.compile(r"[a-f0-9]{64}")
_READ_CHUNK = 65536
_INDEPENDENCE_GAPS = (
    "results are candidate-authored per-case JUnit produced inside the "
    "sandbox that ran the tested code; independent capture unavailable in the "
    "approved sandbox",
    "candidate identity is the declared digest recorded with the candidate "
    "evidence, not a stored engine-side staging binding",
    "authenticated executor receipt acceptance unavailable",
)


def _read_output(raw):
    if type(raw) is not str or not Path(raw).is_absolute():
        raise ContractError("Absolute retained-output path required")
    path = Path(raw)
    try:
        # O_NONBLOCK (same no-follow pattern as identity.read_source) makes the
        # open itself return instead of blocking on a FIFO/pipe with no writer;
        # the fstat type/single-link/size checks below still refuse every
        # non-regular target without waiting for another process.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ContractError("Retained output unavailable") from error
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > MAX_OUTPUT_BYTES
        ):
            raise ContractError("Unsafe or oversized retained-output file")
        data = bytearray()
        while True:
            chunk = os.read(fd, _READ_CHUNK)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_OUTPUT_BYTES:
                raise ContractError("Retained output exceeds bound")
        return bytes(data)
    except OSError as error:
        raise ContractError("Retained output unavailable") from error
    finally:
        os.close(fd)


def record(store, arguments):
    job_id = identifier(arguments["job"])
    phase = arguments["phase"]
    if phase not in PHASES:
        raise ContractError("Unknown evidence phase")
    digest = arguments["source_digest"]
    if type(digest) is not str or not SOURCE_DIGEST.fullmatch(digest):
        raise ContractError("Invalid declared source digest")
    job = store.get(job_id)
    live = snapshot(job["repo"])
    if live["digest"] != job["assessment"]["source_digest"]:
        raise ContractError(
            "Assessed source changed; record evidence against a fresh assessment"
        )
    if phase == "baseline" and digest != job["assessment"]["source_digest"]:
        raise ContractError("Baseline evidence must bind the assessed source identity")
    expectation = load_expectation(dumps(arguments["expectation"]))
    evaluation = evaluate_output(_read_output(arguments["output"]), expectation)
    if not evaluation["accepted"]:
        raise ContractError(
            "Run output refused by trusted evaluator: "
            + "; ".join(evaluation["problems"])[:500]
        )
    store.record_evaluation(job_id, phase, digest, expectation, evaluation)
    return {
        "schema_version": 1,
        "job_id": job_id,
        "phase": phase,
        "source_digest": digest,
        "expectation_digest": expectation["digest"],
        "expected_count": evaluation["expected_count"],
        "results_recorded": len(evaluation["cases"]),
        "accepted": True,
        "grade": GRADE,
        "proof": "NOT_PROVEN",
        "evaluation_sha256": evaluation["evaluation_sha256"],
        "execution_performed": False,
    }


def comparison(job, recorded):
    """Read-only comparison for compare/report; never launches anything."""
    missing = list(job["assessment"]["missing_evidence"])
    result = {
        "schema_version": 1,
        "job_id": job["job_id"],
        "scope": job["goal"],
        "verdict": "NOT_PROVEN",
        "source_digest": job["assessment"]["source_digest"],
        "execution_performed": False,
        "missing_evidence": missing,
        "compared_cases": 0,
        "approved_differences": [],
    }
    if not recorded:
        missing.append(
            "No accepted executor receipt pair is stored for this assessment job"
        )
        return result
    live = snapshot(job["repo"])
    if live["digest"] != job["assessment"]["source_digest"]:
        raise ContractError(
            "Assessed source changed; recorded evidence is stale for this job"
        )
    for row in recorded:
        evaluation = row["evaluation"]
        if row["expectation_digest"] != evaluation.get("expectation_digest"):
            raise ContractError("Stored evidence pairing mismatch")
    if len({row["phase"] for row in recorded}) == 1:
        only = recorded[0]["phase"]
        missing_phase = "candidate" if only == "baseline" else "baseline"
        missing.append(
            f"Recorded evidence covers only the {only} phase; "
            f"{missing_phase} evidence not recorded"
        )
        return result
    baseline = next(row for row in recorded if row["phase"] == "baseline")
    if baseline["source_digest"] != live["digest"]:
        raise ContractError(
            "Baseline evidence is stale: source changed since it was recorded"
        )
    candidate = next(row for row in recorded if row["phase"] == "candidate")
    from .evaluator import compare_evaluations

    inner = compare_evaluations(baseline["evaluation"], candidate["evaluation"])
    result["comparison"] = inner
    result["compared_cases"] = len(inner["cases"])
    missing.extend(_INDEPENDENCE_GAPS)
    return result


def protocol():
    """Public descriptor of the owned junit-stdout-v1 producer program."""
    from .runner import PROGRAM, PROTOCOL

    return {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "producer_sha256": hashlib.sha256(PROGRAM.encode()).hexdigest(),
        "producer_b64": base64.b64encode(PROGRAM.encode()).decode(),
        "note": (
            "Run this operator producer only inside approved sandbox "
            "boundaries; captured results stay candidate-authored and are "
            "never proof. Wire-format misuse of any marker line is refused by "
            "the trusted evaluator."
        ),
        "execution_performed": False,
    }
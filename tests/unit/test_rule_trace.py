"""Rule citations stay lexical until a fresh authenticated review and links."""

import hashlib

from hermes_modernisation.jsonio import dumps
from hermes_modernisation.rule_trace import build, validate_trace

JOB = {
    "job_id": "job",
    "assessment": {"source_digest": "a" * 64},
    "behaviour_contract": {"digest": "b" * 64},
}


def rule():
    return {
        "id": "double",
        "text": "double the value",
        "source_refs": [
            {"path": "app.py", "line_start": 1, "line_end": 2, "sha256": "c" * 64}
        ],
        "case_ids": ["fresh_0"],
    }


def review(rule_value, *, current=None):
    digest = hashlib.sha256(dumps(rule_value)).hexdigest()
    return {
        "id": "review-1",
        "rule_id": rule_value["id"],
        "rule_digest": digest,
        "current_rule_digest": current or digest,
        "authenticated": True,
    }


def evaluation(phase, *, matched=True, rule_id="double"):
    return {
        "phase": phase,
        "evaluation": {
            "cases": [
                {
                    "id": "fresh_0",
                    "matches_expected": matched,
                    "rule_ids": [rule_id],
                }
            ]
        },
    }


def test_lexical_rule_never_becomes_reviewed_or_executed():
    trace = build(JOB, [rule()], [], [])
    assert trace["coverage"] == "unverified"
    assert trace["lexical_only"] is True
    assert trace["rules"][0]["status"] == "candidate_only"
    assert trace["reviewed"] == 0
    validate_trace(trace)


def test_fresh_review_without_cases_stays_unexecuted():
    value = rule()
    trace = build(JOB, [value], [review(value)], [])
    assert trace["rules"][0]["status"] == "reviewed_unexecuted"
    assert trace["coverage"] == "unverified"


def test_both_phases_passing_verify_coverage():
    value = rule()
    trace = build(
        JOB,
        [value],
        [review(value)],
        [evaluation("baseline"), evaluation("candidate")],
    )
    assert trace["rules"][0]["status"] == "reviewed_executed"
    assert trace["coverage"] == "verified"
    assert trace["executed"] == 1
    assert trace["lexical_only"] is False


def test_stale_review_is_visible_and_never_counts():
    value = rule()
    trace = build(
        JOB,
        [value],
        [review(value, current="d" * 64)],
        [evaluation("baseline"), evaluation("candidate")],
    )
    assert trace["rules"][0]["status"] == "review_stale"
    assert trace["coverage"] == "unverified"
    assert trace["failed"] == 1


def test_failed_or_orphan_links_block_coverage():
    value = rule()
    failed = build(
        JOB,
        [value],
        [review(value)],
        [evaluation("baseline", matched=False), evaluation("candidate")],
    )
    assert failed["rules"][0]["status"] == "reviewed_failed"
    assert failed["coverage"] == "unverified"
    orphan = build(
        JOB,
        [value],
        [review(value)],
        [evaluation("baseline", rule_id="invented"), evaluation("candidate", rule_id="invented")],
    )
    assert orphan["orphan_links"] == ["invented"]
    assert orphan["coverage"] == "unverified"

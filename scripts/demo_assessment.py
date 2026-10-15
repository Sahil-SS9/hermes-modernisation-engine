"""Real approved-clone assessment only, never a behavioural run."""

import json
import base64
import hashlib
from pathlib import Path
from hermes_modernisation.service import Engine
from hermes_modernisation.identity import snapshot

engine = Engine(Path("/tmp/jobs"))
job = engine.invoke(
    "assess",
    {
        "repo": "/benchmark",
        "goal": "Python 3.14 and FastAPI upgrade",
        "request_id": "real-benchmark",
    },
)
assessment = job["assessment"]
counts = assessment["detail_counts"]
for section, expected in counts.items():
    seen = 0
    for page in range(len(assessment["detail_pages"][section])):
        value = engine.invoke(
            "inventory", {"job": job["job_id"], "section": section, "page": page}
        )
        seen += len(value["items"])
        assert value["has_more"] == (
            page + 1 < len(assessment["detail_pages"][section])
        )
    assert seen == expected, (section, seen, expected)
planned = engine.invoke("plan", {"job": job["job_id"], "revision": 0})
result = engine.invoke("compare", {"job": job["job_id"]})
assert snapshot(Path("/benchmark"))["digest"] == assessment["source_digest"]
report = engine.invoke("report", {"job": job["job_id"]})
raw = report["html"].encode()
print(
    "REPORT_ARTIFACT_JSON="
    + json.dumps(
        {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content_base64": base64.b64encode(raw).decode(),
        }
    )
)
print(
    json.dumps(
        {
            "file_count": assessment["file_count"],
            "source_digest": assessment["source_digest"],
            "inventory_counts": counts,
            "all_inventory_pages_verified": True,
            "parse_errors": assessment["parse_errors"],
            "unsupported_paths": assessment["unsupported_paths"],
            "state": planned["state"],
            "verdict": result["verdict"],
            "execution_performed": False,
            "source_unchanged": True,
        },
        sort_keys=True,
    )
)

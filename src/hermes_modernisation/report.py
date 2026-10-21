"""Deterministic offline engineering-preview report; never interprets repo HTML."""

from html import escape


def render(job, comparison):
    def cell(value):
        return escape(str(value), quote=True)

    assessment = job["assessment"]
    counts = assessment.get("detail_counts", {})
    facts = [
        ("State", job["state"]),
        ("Goal", job["goal"]),
        ("Source identity", assessment["source_digest"]),
        ("Files inventoried", assessment.get("file_count", "unknown")),
        ("Lexical symbols", counts.get("symbols", "unknown")),
        (
            "Assertion-location candidates (not reviewed rules)",
            counts.get("rules", "unknown"),
        ),
        ("Compared execution cases", comparison["compared_cases"]),
        (
            "Business-rule coverage",
            comparison.get("rule_trace", {}).get("coverage", "unknown"),
        ),
        ("Approved normalisations", len(comparison.get("approved_differences", []))),
        ("Model/API cost", "unknown"),
    ]
    rows = "".join(
        "<tr><th>" + cell(name) + "</th><td>" + cell(value) + "</td></tr>"
        for name, value in facts
    )
    gaps = "".join(
        "<li>" + cell(value) + "</li>" for value in comparison["missing_evidence"]
    )
    unsupported = "".join(
        "<li>" + cell(value) + "</li>"
        for value in assessment.get("unsupported_paths", [])
    )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Modernisation Engine — NOT_PROVEN</title><style>body{font:17px/1.5 system-ui,sans-serif;max-width:960px;margin:3rem auto;padding:0 1.5rem;color:#18212a;background:#fafafa}h1{line-height:1.2}table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #ccc;text-align:left;padding:.7rem;overflow-wrap:anywhere}th{width:38%}.verdict{background:#fff2cf;border-left:5px solid #926000;padding:1rem}li{margin:.5rem 0;overflow-wrap:anywhere}</style>
<h1>Modernisation Engine</h1><p class="verdict"><strong>NOT_PROVEN</strong> — source assessment only. This is not a behavioural migration acceptance or release sign-off.</p><table>"""
        + rows
        + """</table><h2>Missing evidence</h2><ul>"""
        + gaps
        + """</ul><h2>Unsupported lexical parsing</h2><p>Only Python AST facts are extracted. Other code files remain unverified; arbitrary business rules are not inferred.</p><ul>"""
        + unsupported
        + """</ul><h2>Safety and provenance</h2><p>No repository program or model is run by report generation. This private engineering preview makes no equivalence, cost-saving or production-readiness claim. Source instructions and names are untrusted data. Rendering is escaped, offline and contains no scripts, remote fonts, analytics or outbound assets.</p></html>"""
    )

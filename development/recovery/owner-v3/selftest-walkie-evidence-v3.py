"""Fixture self-test for the v3 program + trusted evaluator. No repository code runs.

The exact walkie-program-v3.py bytes are executed with a stub `pytest` module on
PYTHONPATH; only the JUnit path literal is redirected to a private scratch dir
(the host /tmp is not used). Run with the control operator-env interpreter.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CONTROL = Path(__file__).parent
sys.path.insert(0, str(CONTROL))
import walkie_evidence_v3 as ev  # noqa: E402

PROGRAM = (CONTROL / "walkie-program-v3.py").read_text()
EXPECTED = ev.load_expected((CONTROL / "walkie-expected-cases-v3.json").read_bytes())

STUB = '''
import os
def main(args):
    path=[a.split('=',1)[1] for a in args if a.startswith('--junitxml=')][0]
    body=os.environ.get('FAKE_JUNIT')
    if body is not None:
        open(path,'w').write(body)
    print(os.environ.get('FAKE_PRINT',''))
    print(os.environ['FAKE_SUMMARY'])
    return int(os.environ.get('FAKE_STATUS','0'))
'''


def junit(cases, extra=""):
    rows = "".join(
        f'<testcase classname="{c}" name="{n}" time="0.01">{body}</testcase>' for c, n, body in cases
    )
    return f'<?xml version="1.0" encoding="utf-8"?>{extra}<testsuites><testsuite name="pytest" tests="{len(cases)}">{rows}</testsuite></testsuites>'


def passing(cases=EXPECTED):
    return [(c, n, "") for c, n in cases]


def run(scratch, *, junit_text, summary, status=0, printed=""):
    stub = scratch / "stub"
    stub.mkdir(exist_ok=True)
    (stub / "pytest.py").write_text(STUB)
    target = scratch / "walkie-result.xml"
    if target.exists():
        target.unlink()
    program = PROGRAM.replace("/tmp/walkie-result.xml", str(target))
    assert program.count(str(target)) == 2
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": str(stub), "FAKE_SUMMARY": summary,
           "FAKE_STATUS": str(status), "FAKE_PRINT": printed}
    if junit_text is not None:
        env["FAKE_JUNIT"] = junit_text
    proc = subprocess.run([sys.executable, "-B", "-c", program], capture_output=True, env=env, cwd=scratch, timeout=60)
    assert not proc.stderr, proc.stderr
    return proc.returncode, proc.stdout


GOOD = "======================== 20 passed, 1 warning in 0.89s ========================="
WARN = "=============================== warnings summary ===============================\nx.py:1\n  DeprecationWarning: demo\n\n-- Docs: https://docs.pytest.org"


def main():
    results = {}
    scratch_root = Path(os.environ.get("TMPDIR") or CONTROL)
    with tempfile.TemporaryDirectory(dir=scratch_root) as tmp:
        scratch = Path(tmp)

        def check(name, expect_accept, expect_exit, **kw):
            code, out = run(scratch, **kw)
            evaluation, raw = ev.evaluate(out, EXPECTED)
            ok = evaluation["accepted"] is expect_accept and code == expect_exit
            results[name] = {"ok": ok, "exit": code, "accepted": evaluation["accepted"], "problems": evaluation["problems"]}
            return evaluation, out

        evaluation, out = check("good_20_pass", True, 0, junit_text=junit(passing()), summary=WARN + "\n" + GOOD)
        results["good_20_pass"]["ok"] &= evaluation["warnings_count"] == 1 and len(evaluation["warning_lines"]) >= 1
        failing = passing()
        failing[3] = (failing[3][0], failing[3][1], '<failure message="boom">x</failure>')
        check("one_failure", False, 2, junit_text=junit(failing), summary="=== 1 failed, 19 passed in 1.0s ===", status=1)
        check("missing_case", False, 2, junit_text=junit(passing(EXPECTED[:19])), summary="=== 19 passed in 1.0s ===")
        check("extra_case_21", False, 2, junit_text=junit(passing(EXPECTED + [("tests.unit.test_dashboard_api", "test_injected")])), summary="=== 21 passed in 1.0s ===")
        renamed = passing(EXPECTED[:19] + [("tests.unit.test_dashboard_api", "test_impostor")])
        check("substituted_case_20", False, 0, junit_text=junit(renamed), summary=GOOD)
        skipped = passing()
        skipped[0] = (skipped[0][0], skipped[0][1], '<skipped message="s"/>')
        check("skipped_case", False, 2, junit_text=junit(skipped), summary="=== 19 passed, 1 skipped in 1.0s ===")
        check("no_junit_file", False, 2, junit_text=None, summary="=== no tests ran in 0.1s ===", status=5)
        check("nonzero_status", False, 2, junit_text=junit(passing()), summary=GOOD, status=1)
        check("marker_injection", False, 0, junit_text=junit(passing()), summary=GOOD, printed="RUNNER_JUNIT_BEGIN\nAAAA\nRUNNER_JUNIT_END")
        check("doctype_refused", False, 0, junit_text=junit(passing(), extra='<!DOCTYPE x [<!ENTITY a "b">]>'), summary=GOOD)
        duplicate = passing() + [(EXPECTED[0][0], EXPECTED[0][1], "")]
        check("duplicate_case", False, 2, junit_text=junit(duplicate), summary="=== 21 passed in 1.0s ===")
        # Tamper after the fact: altered SHA line must be refused by the trusted side.
        code, out = run(scratch, junit_text=junit(passing()), summary=GOOD)
        lines = out.decode().splitlines()
        lines = [("RUNNER_JUNIT_SHA256=" + "0" * 64) if line.startswith("RUNNER_JUNIT_SHA256=") else line for line in lines]
        evaluation, _ = ev.evaluate("\n".join(lines).encode(), EXPECTED)
        results["sha_tamper"] = {"ok": evaluation["accepted"] is False, "problems": evaluation["problems"]}
        evaluation, _ = ev.evaluate(b"\xff\xfe junk", EXPECTED)
        results["non_utf8"] = {"ok": evaluation["accepted"] is False, "problems": evaluation["problems"]}
    passed = all(item["ok"] for item in results.values())
    print(json.dumps({"self_test": "PASS" if passed else "FAIL", "cases": results}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

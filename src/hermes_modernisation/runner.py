"""Owned junit-stdout-v1 protocol producer for operator-prepared test runs.

PROGRAM is a self-contained script executed inside an approved sandbox (never
by the engine itself): it invokes pytest on caller-chosen arguments, bounds the
artifacts, retains the raw JUnit XML between single BEGIN/END markers and
declares status, counts and environment. evaluator.evaluate_output is the only
consumer of the wire format and re-derives every count from the embedded
JUnit, so any forged or inconsistent declaration is refused. Capture still
happens inside the environment that ran the tests: results remain
candidate-authored per-case JUnit and never constitute proof.
"""

PROTOCOL = "junit-stdout-v1"

PROGRAM = '''"""Bounded producer: retain raw JUnit and declare status/counts/env.

Usage: producer.py <pytest arguments...>  (run inside approved sandboxes only)
"""

import base64
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

MAX_JUNIT_BYTES = 1048576
MAX_OUTPUT_BYTES = 4194304


def _counts(path):
    root = ElementTree.parse(path).getroot()
    cases = list(root.iter("testcase"))
    return {
        "collected": len(cases),
        "failures": sum(1 for case in cases if case.find("failure") is not None),
        "errors": sum(1 for case in cases if case.find("error") is not None),
        "skipped": sum(1 for case in cases if case.find("skipped") is not None),
    }


def _fail(message, captured=b""):
    if captured:
        sys.stdout.write(captured.decode("utf-8", errors="replace"))
        sys.stdout.flush()
    sys.stderr.write("modernise-producer refused: " + message + "\\n")
    return 62


def main(argv):
    if len(argv) > 30 or any(len(argument) > 300 for argument in argv):
        return _fail("argument bounds exceeded")
    if any(
        argument in ("--junitxml", "-p") or argument.startswith("--junitxml=")
        for argument in argv
    ):
        return _fail("reserved pytest options are not accepted")
    workdir = tempfile.mkdtemp(prefix="modernise-producer-")
    try:
        junit = os.path.join(workdir, "junit.xml")
        command = [
            sys.executable, "-B", "-m", "pytest", *argv,
            "-p", "no:cacheprovider", "--junitxml=" + junit,
        ]
        try:
            done = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return _fail("pytest run exceeded the producer deadline")
        text = done.stdout.decode("utf-8", errors="replace")
        if len(text) > MAX_OUTPUT_BYTES:
            return _fail("pytest output exceeds bound")
        if not os.path.isfile(junit):
            return _fail("pytest produced no JUnit artifact", done.stdout)
        with open(junit, "rb") as stream:
            raw = stream.read()
        if not raw or len(raw) > MAX_JUNIT_BYTES:
            return _fail("JUnit artifact missing or over bound", done.stdout)
        try:
            counts = _counts(junit)
        except ElementTree.ParseError as error:
            return _fail("JUnit artifact unparseable: " + str(error), done.stdout)
        if not text.endswith("\\n"):
            text += "\\n"
        environment = {"argv": " ".join(argv), "python": platform.python_version(),
                       "system": platform.system()}
        payload = json.dumps(environment, sort_keys=True)
        if len(payload) > 512:
            return _fail("environment description exceeds bound")
        sys.stdout.write(text)
        sys.stdout.write("RUNNER_PYTEST_STATUS=" + str(done.returncode) + "\\n")
        sys.stdout.write("RUNNER_COUNTS_JSON=" + json.dumps(counts, sort_keys=True) + "\\n")
        sys.stdout.write("RUNNER_ENV_JSON=" + payload + "\\n")
        sys.stdout.write("RUNNER_JUNIT_BYTES=" + str(len(raw)) + "\\n")
        sys.stdout.write("RUNNER_JUNIT_SHA256=" + hashlib.sha256(raw).hexdigest() + "\\n")
        sys.stdout.write("RUNNER_JUNIT_BEGIN\\n")
        sys.stdout.write(base64.b64encode(raw).decode() + "\\n")
        sys.stdout.write("RUNNER_JUNIT_END\\n")
        sys.stdout.flush()
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
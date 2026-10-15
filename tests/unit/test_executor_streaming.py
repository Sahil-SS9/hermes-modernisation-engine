"""Real bounded-pipe tests inside the development sandbox, not Docker runtime proof."""

import subprocess
import sys
from hermes_modernisation.executor import Executor


def test_output_limit_is_enforced_during_streaming(monkeypatch):
    popen = subprocess.Popen

    def launch(*args, **kwargs):
        return popen(
            [sys.executable, "-B", "-c", 'import os; os.write(1,b"x"*1000000)'],
            **kwargs,
        )

    monkeypatch.setattr(subprocess, "Popen", launch)
    raw, timed_out, truncated = Executor._collect("fixture", 3, 1024)
    assert len(raw) == 1024 and truncated and not timed_out


def test_timeout_is_enforced_even_without_output(monkeypatch):
    popen = subprocess.Popen

    def launch(*args, **kwargs):
        return popen(
            [sys.executable, "-B", "-c", "import time; time.sleep(10)"], **kwargs
        )

    monkeypatch.setattr(subprocess, "Popen", launch)
    raw, timed_out, truncated = Executor._collect("fixture", 0.05, 1024)
    assert raw == b"" and timed_out and not truncated


def test_normal_output_collected_without_synthetic_test_counts(monkeypatch):
    popen = subprocess.Popen

    def launch(*args, **kwargs):
        return popen([sys.executable, "-B", "-c", 'print("3 tests passed")'], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", launch)
    raw, timed_out, truncated = Executor._collect("fixture", 3, 1024)
    assert raw == b"3 tests passed\n" and not timed_out and not truncated

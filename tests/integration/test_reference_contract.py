"""Selected immutable-reference conformance; not blanket reference-suite parity."""

import hashlib
import importlib.util
from pathlib import Path
import pytest
from hermes_modernisation.compare import compare_cases


@pytest.mark.parametrize(
    "before,after",
    [
        ("same", "same"),
        ("", ""),
        ("abc", "abd"),
        ("", "x"),
        ("x", ""),
        ("1", "2"),
        ("é", "e"),
    ],
)
def test_raw_output_equality_matches_pinned_reference(before, after):
    path = Path("/reference/scripts/compare.py")
    assert path.is_file(), (
        "Pinned external comparator reference must be mounted for conformance"
    )
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "42da2625792868cc2f22df05bd6d26f05c7f6144159556ea41f5e2f41f1584fb"
    )
    spec = importlib.util.spec_from_file_location("pinned_comparator_reference", path)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)

    def case(output):
        return {
            "id": "one",
            "input_digest": "a" * 64,
            "output": output,
            "exception": None,
            "side_effects": [],
        }

    result = compare_cases([case(before)], [case(after)])
    same = reference.first_diff(before.encode(), after.encode()) is None
    assert result["same"] == int(same)
    assert result["differs"] == int(not same)
    assert result["verdict"] == "NOT_PROVEN"

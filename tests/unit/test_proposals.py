import hashlib
import pytest
from hermes_modernisation.proposals import validate_proposal, stage_candidate
from hermes_modernisation.identity import snapshot
from hermes_modernisation.jsonio import ContractError


def fixture(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    (repo / "module.py").write_text("def double(x):\n    return x*2\n")
    proposal = {
        "schema_version": 1,
        "source_digest": snapshot(repo)["digest"],
        "goal": "modernise",
        "changes": [
            {
                "path": "module.py",
                "before_sha256": hashlib.sha256(
                    (repo / "module.py").read_bytes()
                ).hexdigest(),
                "replacement": "def double(x):\n    return x+x\n",
            }
        ],
        "allowed_paths": ["module.py"],
        "planned_differences": [],
    }
    return repo, proposal


def test_separate_candidate_keeps_original_and_tests_unchanged(tmp_path):
    repo, p = fixture(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests/test_api.py").write_text("assert True\n")
    p["source_digest"] = snapshot(repo)["digest"]
    destination = tmp_path / "candidate"
    result = stage_candidate(repo, destination, p)
    assert (repo / "module.py").read_text().endswith("return x*2\n")
    assert (destination / "module.py").read_text().endswith("return x+x\n")
    assert (destination / "tests/test_api.py").read_bytes() == (
        repo / "tests/test_api.py"
    ).read_bytes()
    assert result["source_digest"] != result["candidate_digest"]
    assert result["approved"] is False and result["execution_performed"] is False
    with pytest.raises(ContractError):
        stage_candidate(repo, destination, p)


@pytest.mark.parametrize(
    "path",
    [
        "../escape",
        "/etc/passwd",
        "tests/test_api.py",
        ".git/config",
        "oracle.json",
        "pyproject.toml",
    ],
)
def test_protected_or_unapproved_paths_refused(tmp_path, path):
    repo, p = fixture(tmp_path)
    p["changes"][0]["path"] = path
    with pytest.raises(ContractError):
        validate_proposal(repo, p)


def test_stale_input_missing_bytes_and_arbitrary_fields_refused(tmp_path):
    repo, p = fixture(tmp_path)
    p["changes"][0]["before_sha256"] = "b" * 64
    with pytest.raises(ContractError):
        validate_proposal(repo, p)
    repo, p = fixture(tmp_path / "second")
    p["approved"] = True
    with pytest.raises(ContractError):
        validate_proposal(repo, p)

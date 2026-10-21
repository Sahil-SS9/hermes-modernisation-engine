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


def _dependency_proposal(repo, path):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("fixture-package==1\n")
    return {
        "schema_version": 1,
        "source_digest": snapshot(repo)["digest"],
        "goal": "modernise",
        "changes": [
            {
                "path": path,
                "before_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "replacement": "fixture-package==2\n",
            }
        ],
        "allowed_paths": [path],
        "planned_differences": [],
    }


@pytest.mark.parametrize(
    "path",
    [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements_dev.txt",
        "requirements_prod.txt",
        "requirements/dev.txt",
        "requirements/base.in",
        "bun.lock",
    ],
)
def test_dependency_manifest_variants_are_refused_even_when_allowlisted(
    tmp_path, path
):
    repo, _ = fixture(tmp_path)
    proposal = _dependency_proposal(repo, path)
    with pytest.raises(ContractError, match="Protected"):
        validate_proposal(repo, proposal)
    with pytest.raises(ContractError, match="Protected"):
        stage_candidate(repo, tmp_path / "candidate", proposal)
    assert not (tmp_path / "candidate").exists()


def test_ordinary_requirements_module_is_not_a_dependency_manifest(tmp_path):
    repo, _ = fixture(tmp_path)
    module = repo / "src/requirements.py"
    module.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n")
    proposal = {
        "schema_version": 1,
        "source_digest": snapshot(repo)["digest"],
        "goal": "modernise",
        "changes": [
            {
                "path": "src/requirements.py",
                "before_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
                "replacement": "VALUE = 2\n",
            }
        ],
        "allowed_paths": ["src/requirements.py"],
        "planned_differences": [],
    }
    validated, _ = validate_proposal(repo, proposal)
    result = stage_candidate(repo, tmp_path / "candidate", validated)
    assert (tmp_path / "candidate/src/requirements.py").read_text() == "VALUE = 2\n"
    assert result["changed_paths"] == ["src/requirements.py"]

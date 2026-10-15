"""Owner-approved real candidate metadata; not behavioural equivalence evidence."""

import tomllib
from pathlib import Path


def test_python314_and_host_dashboard_dependencies_are_declared():
    root = Path("/benchmark")
    assert root.is_dir(), "Approved isolated benchmark clone must be mounted read-only"
    data = tomllib.loads((root / "pyproject.toml").read_text())
    assert data["project"]["requires-python"] == ">=3.11,<3.15"
    assert data["project"]["optional-dependencies"]["dashboard"] == ["fastapi==0.133.1"]
    assert "fastapi==0.133.1" in data["dependency-groups"]["dev"]
    assert "httpx==0.28.1" in data["dependency-groups"]["dev"]
    assert '"3.14"' in (root / ".github/workflows/ci.yml").read_text()

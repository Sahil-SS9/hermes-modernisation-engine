"""Build and smoke only in disposable sandbox storage. Emit real artifact bytes."""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path


def main():
    if not Path("/work").is_dir() or os.environ.get("HOME") != "/tmp":
        raise RuntimeError("Use the approved disposable build container")
    source = Path("/source")
    stage = Path("/work/source")
    dist = Path("/work/dist")
    shutil.copytree(
        source,
        stage,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "dist",
            "build",
            "*.egg-info",
        ),
    )
    result = subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            "/opt/hermes/.venv/bin/python",
            "--out-dir",
            str(dist),
        ],
        cwd=stage,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    wheel = next(dist.glob("*.whl"))
    subprocess.run(
        ["uv", "venv", "--python", "/usr/local/bin/python3.14", "/work/consumer"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            "/work/consumer/bin/python",
            "--no-index",
            "--no-deps",
            str(wheel),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    repo = Path("/work/example")
    repo.mkdir()
    (repo / "example.py").write_text("def double(x):\n    return x*2\n")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    command = [
        "/work/consumer/bin/python",
        "-m",
        "hermes_modernisation",
        "--data-dir",
        "/work/jobs",
    ]
    run = subprocess.run(
        command
        + [
            "assess",
            "--repo",
            str(repo),
            "--goal",
            "smoke",
            "--request-id",
            "wheel-smoke",
        ],
        cwd="/work",
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    job = json.loads(run.stdout)
    assert job["assessment"]["file_count"] == 1 and job["state"] == "ASSESSED"
    read = subprocess.run(
        command + ["status", "--job", job["job_id"]],
        cwd="/work",
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(read.stdout) == job
    denied = subprocess.run(
        command + ["run", "--job", job["job_id"]],
        cwd="/work",
        env=env,
        capture_output=True,
        text=True,
    )
    assert denied.returncode == 2 and "EXECUTION_UNAVAILABLE" in denied.stdout
    archive = dist / "modernisation-engine-preview.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        paths = [
            stage / "__init__.py",
            stage / "plugin.yaml",
            stage / "pyproject.toml",
            stage / "uv.lock",
            stage / "README.md",
        ]
        paths += sorted((stage / "src").rglob("*.py"))
        paths += [
            stage / ("docs/" + name)
            for name in ("provenance.md", "threat-model.md", "compatibility.md")
        ]
        for path in paths:
            name = "modernisation-engine/" + path.relative_to(stage).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive) as contents:
        assert contents.testzip() is None
        assert all(
            not name.startswith("/") and ".." not in name.split("/")
            for name in contents.namelist()
        )
        assert "modernisation-engine/plugin.yaml" in contents.namelist()
        assert not any(
            "/tests/" in name
            or "/evidence/" in name
            or "/reference/" in name
            or "/approvals/" in name
            for name in contents.namelist()
        )
        contents.extractall("/work/unpacked")
    unpacked = Path("/work/unpacked/modernisation-engine")
    validation = subprocess.run(
        [
            "/opt/hermes/.venv/bin/hermes",
            "plugins",
            "validate",
            str(unpacked),
            "--json",
        ],
        cwd="/work",
        env=env,
        capture_output=True,
        text=True,
    )
    assert validation.returncode == 0, validation.stdout + validation.stderr
    assert json.loads(validation.stdout)["ok"] is True
    home = Path("/work/host-home")
    (home / "plugins").mkdir(parents=True)
    shutil.move(str(unpacked), home / "plugins/modernisation-engine")
    (home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - modernisation-engine\n"
    )
    host_env = dict(
        env,
        HOME=str(home),
        HERMES_HOME=str(home),
        HERMES_BUNDLED_PLUGINS=str(home / "empty"),
        HERMES_ENABLE_PROJECT_PLUGINS="0",
    )
    loaded = subprocess.run(
        ["/opt/hermes/.venv/bin/hermes", "modernise", "status"],
        cwd=home,
        env=host_env,
        capture_output=True,
        text=True,
    )
    assert loaded.returncode == 0, loaded.stdout + loaded.stderr
    assert json.loads(loaded.stdout)["implementation_status"] == "READ_ONLY_PREVIEW"
    for path in (wheel, archive):
        data = path.read_bytes()
        print(
            "ARTIFACT_JSON="
            + json.dumps(
                {
                    "filename": path.name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                    "content_base64": base64.b64encode(data).decode(),
                }
            )
        )
    print(
        "BUILD_SMOKE_JSON="
        + json.dumps(
            {
                "wheel_installed_in_disposable_venv": True,
                "assess_status_roundtrip": True,
                "unauthorised_execution_refused": True,
                "zip_integrity": True,
                "packaged_directory_native_load_and_validation": True,
                "private_fixture_and_evidence_paths_excluded": True,
                "scope": "read-only preview, not full migration engine",
            }
        )
    )


if __name__ == "__main__":
    main()

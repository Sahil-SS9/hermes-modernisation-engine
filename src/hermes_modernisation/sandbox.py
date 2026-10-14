"""Fail-closed container launch policy; not a grant or execution endpoint."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxSpec:
    image: str
    source: Path
    argv: tuple[str, ...]
    name: str


def docker_argv(spec: SandboxSpec) -> list[str]:
    """Build a fixed resource-limited, credential-free Docker launch policy.

    Pure construction is NOT execution authority. A trusted executor must verify
    rootless runtime, exact source identity and an authentic one-use grant.
    """
    if not re.fullmatch(r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}", spec.image):
        raise ValueError("Image must use a full immutable SHA-256 digest")
    if not re.fullmatch(r"modernise-[a-z0-9-]{1,50}", spec.name):
        raise ValueError("Invalid container name")
    if not spec.source.is_absolute() or not spec.source.is_dir():
        raise ValueError("Source must be an existing absolute directory")
    if spec.source != spec.source.resolve(strict=True):
        raise ValueError("Source path must not contain symlinks or ambiguity")
    root = str(spec.source)
    if len(spec.source.parts) < 3 or spec.source.parent in (Path('/home'), Path('/Users')):
        raise ValueError("Broad host directory mounts are forbidden")
    if spec.source.parts[1] in {'etc', 'run', 'proc', 'sys', 'dev', 'var', 'usr', 'boot', 'bin', 'lib', 'lib64', 'root'}:
        raise ValueError("Host system directories are forbidden")
    if any(part in ('.hermes', '.ssh', '.aws', '.config', '.local') for part in spec.source.parts):
        raise ValueError("Host configuration/credential directories are forbidden")
    if any(char in root for char in (',', chr(10), chr(13), chr(0))):
        raise ValueError("Source contains unsafe mount characters")
    if not spec.argv or any(not isinstance(arg, str) or chr(0) in arg for arg in spec.argv):
        raise ValueError("Command must be a nonempty argv of NUL-free strings")
    return [
        'docker', 'run', '--rm', '--pull=never', '--name', spec.name,
        '--network=none', '--read-only', '--cap-drop=ALL',
        '--security-opt=no-new-privileges', '--pids-limit=64',
        '--memory=512m', '--memory-swap=512m', '--cpus=1',
        '--user=65534:65534', '--ulimit', 'nofile=256:256',
        '--ulimit', 'fsize=131072:131072', '--log-driver=none',
        '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m,mode=1777',
        '--tmpfs', '/work:rw,nosuid,nodev,size=128m,mode=1777',
        '--mount', f'type=bind,src={root},dst=/source,readonly,bind-recursive=disabled',
        '--workdir', '/source', '--env', 'PYTHONPATH=/source/src:/source',
        '--env', 'PYTHONDONTWRITEBYTECODE=1', '--env', 'HOME=/tmp',
        '--env', 'TMPDIR=/tmp', spec.image, *spec.argv,
    ]

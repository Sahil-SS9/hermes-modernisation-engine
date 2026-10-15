"""POSIX bounded no-follow source inventory; does not execute repository code."""

import hashlib
import os
import stat
from pathlib import Path
from .jsonio import ContractError, dumps

EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
MAX_FILES = 8000
MAX_FILE_BYTES = 8388608
MAX_TOTAL_BYTES = 67108864


def safe_relative(value):
    if (
        type(value) is not str
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(ord(c) < 32 for c in value)
    ):
        raise ContractError("Invalid relative source path")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ContractError("Ambiguous relative source path")
    if any(part in EXCLUDED for part in value.split("/")):
        raise ContractError("Generated/private path is outside source policy")
    if Path(value).name in {
        ".env",
        "auth.json",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
    }:
        raise ContractError("Credential-bearing filename refused")
    return value


def _signature(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_mode,
        info.st_nlink,
    )


def _directory_fd(root):
    root = Path(root)
    if not root.is_absolute():
        raise ContractError("Absolute source directory required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
            os.close(fd)
            fd = child
        return fd
    except OSError as error:
        os.close(fd)
        raise ContractError("Source ancestor traversal refused") from error


def read_source(root, relative):
    relative = safe_relative(relative)
    directory = _directory_fd(root)
    try:
        for part in relative.split("/")[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            os.close(directory)
            directory = child
        fd = os.open(
            relative.split("/")[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        try:
            before = os.fstat(fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size > MAX_FILE_BYTES
            ):
                raise ContractError("Unsafe source file or byte limit")
            raw = bytearray()
            while True:
                chunk = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_FILE_BYTES:
                    raise ContractError("Source size limit exceeded")
            after = os.fstat(fd)
            if _signature(before) != _signature(after) or len(raw) != after.st_size:
                raise ContractError("Source changed during read")
            return bytes(raw), stat.S_IMODE(after.st_mode)
        finally:
            os.close(fd)
    except OSError as error:
        raise ContractError("Source read refused: " + type(error).__name__) from error
    finally:
        os.close(directory)


def snapshot(root):
    root = Path(root)
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise ContractError("Source root must be an unambiguous absolute directory")
    files = []
    directories = []
    total = 0

    def fail(error):
        raise ContractError("Source traversal incomplete") from error

    try:
        for directory, folders, names in os.walk(root, followlinks=False, onerror=fail):
            folders[:] = sorted(f for f in folders if f not in EXCLUDED)
            for name in folders:
                if (Path(directory) / name).is_symlink():
                    raise ContractError("Directory symlink refused")
                child = Path(directory) / name
                relative = child.relative_to(root).as_posix()
                safe_relative(relative)
                if len(directories) >= MAX_FILES:
                    raise ContractError("Directory inventory limit exceeded")
                directories.append(
                    {"path": relative, "mode": stat.S_IMODE(child.stat().st_mode)}
                )
            for name in sorted(names):
                relative = (Path(directory) / name).relative_to(root).as_posix()
                raw, mode = read_source(root, relative)
                total += len(raw)
                if len(files) >= MAX_FILES or total > MAX_TOTAL_BYTES:
                    raise ContractError("Source inventory limit exceeded")
                files.append(
                    {
                        "path": relative,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "bytes": len(raw),
                        "mode": mode,
                    }
                )
        files.sort(key=lambda value: value["path"])
        return {
            "schema_version": 2,
            "digest": hashlib.sha256(
                dumps(
                    {
                        "files": files,
                        "directories": directories,
                        "identity_policy": "files-and-dirs-v2",
                    }
                )
            ).hexdigest(),
            "directories": directories,
            "files": files,
            "file_count": len(files),
            "total_bytes": total,
            "complete": True,
            "excluded_directories": sorted(EXCLUDED),
            "execution_performed": False,
        }
    except OSError as error:
        raise ContractError("Source inventory incomplete") from error

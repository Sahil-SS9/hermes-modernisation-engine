"""Per-job runtime ownership, held across create/start/collection/cleanup.

A durable lease alone cannot fence an already-paused OS launcher. The OS lock
prevents recovery from racing a late create/start; cooperative cancel signals
are stored independently and do not steal the live worker's lock.
"""

from contextlib import contextmanager
import os
import stat
import sys

from .jsonio import ContractError, identifier
from .operator import private_directory


@contextmanager
def locked(policy, job_id):
    if sys.platform != "linux":
        raise ContractError("EXECUTION_UNAVAILABLE: only the verified Linux rootless backend is supported")
    import fcntl

    identifier(job_id)
    control = policy.workspace / "control"
    control.mkdir(mode=0o700, exist_ok=True)
    private_directory(control)
    directory = control / "runtime-locks"
    directory.mkdir(mode=0o700, exist_ok=True)
    private_directory(directory)
    descriptor = os.open(directory / (job_id + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ContractError("Unsafe runtime ownership lock")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ContractError("Runtime worker still owns this job; request cancellation or wait before explicit recovery") from error
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)

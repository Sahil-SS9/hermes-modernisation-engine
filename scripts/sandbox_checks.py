"""Operator-only Phase 0 sandbox checks; not a plugin execution-authority API.

Fixed scenarios, fixed roots, no arbitrary flags/mounts/env/image/network input.
The owner approved these sandbox development checks in the controlling session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

IMAGE = 'modernise-sandbox-dev@sha256:49808cb0b9909505e906fcef5e0ea373566c96a0508cbc3f60c2fc38de08217f'
ENGINE = Path('/home/kensei/repos/hermes-modernisation-engine')
BENCHMARK = Path('/home/kensei/projects/modernisation-benchmarks/hermes-walkie-talkie')
EVIDENCE = Path('/home/kensei/projects/modernisation-benchmarks/control/evidence')
SCENARIOS = {
    'engine': (ENGINE, ('python', '-B', '-m', 'pytest', 'tests/unit', 'tests/platform', '-p', 'no:cacheprovider', '--strict-markers', '-ra')),
    'lint': (ENGINE, ('ruff', 'check', '--no-cache', 'src', 'tests', 'scripts')),
    'walkie-api': (BENCHMARK, ('python', '-B', '-m', 'pytest', 'tests/unit/test_dashboard_api.py', 'tests/security/test_ws_auth_fails_closed.py', '-p', 'no:cacheprovider', '--strict-markers', '-ra')),
}


def tree_digest(root: Path) -> str:
    """Bind each development run to bounded source bytes, without interpreting them."""
    digest = hashlib.sha256()
    count = 0
    total = 0
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = sorted(name for name in folders if name not in {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache'})
        for name in folders:
            if (Path(directory)/name).is_symlink():
                raise RuntimeError('Source contains a symlink directory; snapshot review required')
        for name in sorted(files):
            path = Path(directory)/name
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise RuntimeError('Source contains a link or special file; snapshot review required')
            count += 1
            size = path.stat().st_size
            total += size
            if count > 10000 or size > 16777216 or total > 134217728:
                raise RuntimeError('Development source identity exceeds bounded policy')
            digest.update(str(path.relative_to(root)).encode())
            digest.update(bytes([0]))
            with path.open('rb') as stream:
                file_hash = hashlib.file_digest(stream, 'sha256').digest()
            digest.update(file_hash)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=SCENARIOS)
    args = parser.parse_args()
    source, argv = SCENARIOS[args.scenario]
    if source.is_symlink() or source.resolve() != source:
        raise RuntimeError('Refusing ambiguous source path')
    info = subprocess.run(['docker', 'info', '--format', '{{json .SecurityOptions}}'], capture_output=True, text=True, timeout=10, check=True)
    if 'name=rootless' not in json.loads(info.stdout):
        raise RuntimeError('Rootless Docker is required')
    name = 'modernise-' + args.scenario + '-' + str(time.time_ns())
    # Only this trusted operator orchestrator runs on the host. Project code,
    # tests and build hooks execute solely inside the contained child.
    sys.path.insert(0, str(ENGINE/'src'))
    from hermes_modernisation.sandbox import SandboxSpec, docker_argv
    command = docker_argv(SandboxSpec(IMAGE, source, argv, name))
    image_index = command.index(IMAGE)
    command[image_index:image_index] = ['--env', 'HYPOTHESIS_STORAGE_DIRECTORY=/tmp/hypothesis']
    EVIDENCE.mkdir(parents=True, exist_ok=True, mode=0o700)
    before = tree_digest(source)
    start = time.monotonic()
    limit = 4194304
    output = bytearray()
    stopped = None
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while selector.get_map():
            if time.monotonic() - start > 120:
                stopped = 'timeout'
                break
            for key, _ in selector.select(timeout=0.2):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if len(output) + len(chunk) > limit:
                    output.extend(chunk[:limit-len(output)])
                    stopped = 'output_limit'
                    break
                output.extend(chunk)
            if stopped:
                break
        if stopped:
            subprocess.run(['docker', 'kill', name], capture_output=True, timeout=10)
            process.kill()
        exit_code = process.wait(timeout=10)
    finally:
        selector.close()
        if process.poll() is None:
            subprocess.run(['docker', 'kill', name], capture_output=True, timeout=10)
            process.kill()
            process.wait(timeout=10)
        if process.stdout is not None:
            process.stdout.close()
    cleanup = subprocess.run(['docker', 'container', 'inspect', name], capture_output=True, text=True, timeout=10)
    after = tree_digest(source)
    record = {'schema_version': 1, 'grade': 'observed-process-exit', 'scenario': args.scenario,
              'source_digest_before': before, 'source_digest_after': after, 'source_unchanged': before == after,
              'argv': command, 'image': IMAGE, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'duration_seconds': time.monotonic()-start, 'exit_code': exit_code,
              'stop_reason': stopped, 'output_complete': stopped is None,
              'output_sha256': hashlib.sha256(output).hexdigest(),
              'container_absence_confirmed': cleanup.returncode != 0 and 'No such' in cleanup.stderr,
              'limits': ['Test results are reported by the test harness; not semantic-equivalence proof.',
                         'This operator development receipt is NOT an owner-signed plugin job execution receipt.']}
    base = EVIDENCE/name
    log = base.with_suffix('.log')
    receipt = base.with_suffix('.json')
    for path, payload in ((log, output), (receipt, json.dumps(record, indent=2).encode())):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
    print(output.decode(errors='replace'))
    print('Evidence:', receipt)
    if not record['container_absence_confirmed'] or not record['source_unchanged']:
        print('Container cleanup or unchanged source not confirmed; refusing PASS')
        return 2
    return 2 if stopped else exit_code


if __name__ == '__main__':
    raise SystemExit(main())

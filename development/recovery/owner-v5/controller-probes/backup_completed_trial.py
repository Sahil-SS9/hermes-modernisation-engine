#!/usr/bin/env python3
"""Create and read-back-verify a private recovery archive; no private keys.

Copies a whitelisted control-input set, the already-verified public result
packet and a consistent read-only backup of the consumed authority ledger.
Never replays, resets, moves or modifies the live ledger or signed inputs.
"""

import hashlib
import io
import json
import os
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path('/home/kensei/projects/modernisation-benchmarks/control/trial-v5')
PACKET = ROOT / 'requests/trial-v5-controller-1792373558572346245/evidence/controller-verification-1792396670485280647'
STATE = json.loads((ROOT / 'ACTIVE-PACKAGE.json').read_bytes())
MANIFEST = json.loads((Path(STATE['approval_directory']) / 'manifest.json').read_bytes())

files = {f'control/{name}': ROOT / name for name in (
    'run-trial-v5.py', 'prepare-trial-v5.py', 'seal-reviewed-trial-v5.py',
    'sign-owner-trial-v5.sh', 'templates/sign-owner-trial-v5.sh.tmpl',
    'EXPECTED-CASES-V4.json', 'ACTIVE-PACKAGE.json',
    'docker/baseline.Dockerfile', 'docker/candidate.Dockerfile',
    'RESULT-trial-v5-20261019.txt', 'RETURN-v5-20261019.md',
)}
files['control/sign-modernisation-v5-auto.sh'] = Path('/home/kensei/handoff/agent-plugin-plans/approvals/sign-modernisation-v5-auto.sh')
files.update({f'actual-result/{path.name}': path for path in PACKET.iterdir() if path.is_file()})
recovery = ROOT / 'recovery'
recovery.mkdir(mode=0o700, exist_ok=True)
archive = recovery / f'completed-trial-v5-{time.time_ns()}.tar.gz'
with tempfile.TemporaryDirectory(prefix='trial-v5-ledger-backup-', dir=os.environ['TMPDIR']) as raw:
    ledger_copy = Path(raw) / 'consumed-authority-ledger.sqlite'
    source = sqlite3.connect('file:' + MANIFEST['execution']['ledger'] + '?mode=ro', uri=True)
    target = sqlite3.connect(ledger_copy)
    try:
        source.backup(target)
        assert target.execute('SELECT COUNT(*) FROM claims').fetchone()[0] == 2
    finally:
        target.close()
        source.close()
    files['state/consumed-authority-ledger.sqlite'] = ledger_copy
    hashes = {}
    with archive.open('xb') as stream:
        archive.chmod(0o600)
        with tarfile.open(fileobj=stream, mode='w:gz') as output:
            for name, path in sorted(files.items()):
                assert path.is_file() and not path.is_symlink()
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
                output.add(path, arcname=name, recursive=False)
            data = (json.dumps({'engine_commit': 'c343e0bbb26f613571dd03602321b74b08b4ecf2',
                                'files': hashes, 'no_private_keys': True,
                                'ledger_claims_consumed': 2}, sort_keys=True, indent=2) + '\n').encode()
            info = tarfile.TarInfo('SOURCE-FILE-HASHES.json')
            info.size, info.mode = len(data), 0o600
            output.addfile(info, io.BytesIO(data))
    with tarfile.open(archive, 'r:gz') as verified:
        manifest = json.loads(verified.extractfile('SOURCE-FILE-HASHES.json').read())
        for name, digest in manifest['files'].items():
            assert hashlib.sha256(verified.extractfile(name).read()).hexdigest() == digest
        assert len(verified.getmembers()) == len(manifest['files']) + 1
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(json.dumps({'archive': str(archive), 'archive_sha256': digest,
                      'verified_input_members': len(hashes), 'read_back_verified': True,
                      'live_authority_ledger_changed': False, 'private_keys_included': False}, indent=2))

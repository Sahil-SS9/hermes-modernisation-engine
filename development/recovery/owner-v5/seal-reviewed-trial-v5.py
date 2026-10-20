#!/usr/bin/env python3
"""Re-seal existing UNUSED trial inputs after controller review.

This does not prepare clones, build images, execute containers/tests, sign,
claim authority or read private keys. Original requests stay byte-identical.
"""

import argparse
import hashlib
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('trial_v5_seal_prep', ROOT / 'prepare-trial-v5.py')
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    source = args.source
    pointer = ROOT / 'ACTIVE-PACKAGE.json'
    if pointer.exists() or pointer.is_symlink():
        raise SystemExit('active pointer already exists; inspect it before any reseal')
    if not source.is_absolute() or source.parent != ROOT / 'requests' or source.resolve() != source:
        raise SystemExit('refusing ambiguous/out-of-scope source package')
    if prep.LEDGER.exists() or Path(prep.SIGN_DIR, 'trial-v5-signatures.txt').exists():
        raise SystemExit('owner signature/claim state exists; do not reseal or reset it')
    prep._verify_identities()  # read-only checks; never prep.main or image builds
    old_raw = (source / 'manifest.json').read_bytes()
    manifest = json.loads(old_raw)
    if manifest['grant']['expires_at_epoch'] <= time.time():
        raise SystemExit('request expiry must not be silently extended')
    requests = {}
    for phase in ('baseline', 'candidate'):
        raw = (source / f'{phase}.request.json').read_bytes()
        body = json.loads(raw)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != manifest['requests'][phase]['request_sha256'] or prep.approvals.canonical(body) != raw:
            raise SystemExit('old request body is changed or noncanonical')
        requests[phase] = {'bytes': raw, 'sha256': digest}
    created = ROOT / 'requests' / f'trial-v5-controller-{time.time_ns()}'
    created.mkdir(mode=0o755)
    manifest['package_binding_schema'] = 'trial-v5-package-v1'
    manifest['runner'] = {'path': str(ROOT / 'run-trial-v5.py'), 'sha256': sha(ROOT / 'run-trial-v5.py')}
    manifest['preparer'] = {'path': str(ROOT / 'prepare-trial-v5.py'), 'sha256': sha(ROOT / 'prepare-trial-v5.py')}
    manifest['signing_script'] = {'path': str(ROOT / 'sign-owner-trial-v5.sh')}
    manifest['controller_reseal'] = {
        'source_package': str(source),
        'source_manifest_sha256': hashlib.sha256(old_raw).hexdigest(),
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'request_bytes_changed': False,
        'images_rebuilt': False,
        'authority_used': False,
    }
    for phase, request in requests.items():
        (created / f'{phase}.request.json').write_bytes(request['bytes'])
    manifest_path = created / 'manifest.json'
    manifest_path.write_bytes(prep.dumps(manifest))
    manifest_sha = sha(manifest_path)
    script = prep._signing_script(
        requests, manifest_path, ROOT / 'run-trial-v5.py',
        manifest['grant']['expires_at_epoch'], manifest['grant']['expires_at'],
        manifest['clone'], manifest['recipe'], manifest['build']['images'], manifest_sha,
    )
    (ROOT / 'sign-owner-trial-v5.sh').write_text(script)
    (ROOT / 'sign-owner-trial-v5.sh').chmod(0o755)
    state = {
        'schema_version': 1, 'approval_directory': str(created),
        'manifest_sha256': manifest_sha,
        'runner_sha256': sha(ROOT / 'run-trial-v5.py'),
        'preparer_sha256': sha(ROOT / 'prepare-trial-v5.py'),
        'signer_sha256': sha(ROOT / 'sign-owner-trial-v5.sh'),
        'expires_at': manifest['grant']['expires_at'],
        'supersedes': str(source), 'signature_required': True,
    }
    pointer = ROOT / 'ACTIVE-PACKAGE.json'
    if pointer.exists():
        raise SystemExit('active pointer already exists; preserve and inspect, never overwrite')
    pointer.write_text(json.dumps(state, sort_keys=True, indent=2) + '\n')
    print(json.dumps(state, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()

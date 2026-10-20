"""Trusted, explicit operator configuration. Never populated from tool arguments.

Only public verification keys are read. No signing, credential lookup, host
configuration mutation, image download or automatic workspace creation exists.
The enrolled owner/host and its files remain the trust root, not a hostile host.
"""

import base64
import os
import re
from pathlib import Path

from .baseline import read_artifact
from .contracts import fields
from .jsonio import ContractError, identifier, loads


def private_directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or not path.is_dir():
        raise ContractError("Existing unambiguous private workspace required")
    info = path.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ContractError("Unsafe private workspace permissions")
    return path


class OperatorPolicy:
    def __init__(self, path, profile, store_root, source):
        if path is None:
            raise ContractError("EXECUTION_UNAVAILABLE: trusted operator configuration required")
        path = Path(path)
        if not path.is_absolute() or path.resolve() != path:
            raise ContractError("Unambiguous private operator configuration required")
        value = loads(read_artifact(path, 65536))
        fields(value, {"schema_version", "profile", "workspace", "public_keys", "images"}, "operator configuration")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["profile"] != profile:
            raise ContractError("Operator configuration version/profile mismatch")
        self.workspace = private_directory(value["workspace"])
        roots = [Path(store_root).resolve(), Path(source).resolve(), self.workspace]
        if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(roots) for b in roots[i + 1:]):
            raise ContractError("Operator workspace, source and private store must not overlap")
        if path.is_relative_to(roots[1]) or path.is_relative_to(self.workspace):
            raise ContractError("Operator trust configuration must be outside source/workspace")
        if any(part in {".hermes", ".ssh", ".aws", ".config", ".local"} for part in self.workspace.parts):
            raise ContractError("Execution workspace cannot be a credential/configuration directory")
        keys = value["public_keys"]
        if type(keys) is not dict or not 1 <= len(keys) <= 20:
            raise ContractError("Enrolled public owner keys required")
        self.public_keys = {}
        for actor, encoded in keys.items():
            identifier(actor)
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as error:
                raise ContractError("Invalid enrolled public key") from error
            if len(raw) != 32:
                raise ContractError("An Ed25519 public verification key is required")
            self.public_keys[actor] = raw
        images = value["images"]
        if type(images) is not list or not 1 <= len(images) <= 20 or any(type(image) is not str or not re.fullmatch(r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}", image) for image in images):
            raise ContractError("Explicit immutable allowed runtime images required")
        self.images = tuple(images)
        self.profile = profile

    def authority(self, *, create=False):
        from .approvals import ExternalAuthority

        root = self.workspace / "control"
        if create:
            root.mkdir(mode=0o700, exist_ok=True)
            private_directory(root)
        return ExternalAuthority(self.public_keys, root / "claims.sqlite")

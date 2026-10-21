"""Bounded dependency-resolution seam, explicitly blocked in this build.

The engine will not infer a lockfile resolution from model text, replay a
previously captured lock as if it had resolved dependencies, or invoke a package
manager without a trusted offline adapter and cache.  The port exists so a
future owner-reviewed adapter has one narrow entry point; the public default is
a named refusal, not a silent replay.
"""

from .jsonio import ContractError

ECOSYSTEMS = {"npm", "pip", "uv"}
BLOCKED = "DEPENDENCY_RESOLUTION_EXPLICITLY_BLOCKED"


class DependencyResolutionBlocked(ContractError):
    def __init__(self, ecosystem, reason):
        super().__init__(f"{BLOCKED}: {ecosystem}: {reason}")
        self.code = BLOCKED
        self.ecosystem = ecosystem
        self.execution_performed = False


def resolve(ecosystem, inputs, *, adapter=None):
    """Resolve dependencies only through an enrolled offline adapter."""
    if ecosystem not in ECOSYSTEMS:
        raise ContractError("Unsupported dependency ecosystem")
    if type(inputs) is not dict or not inputs:
        raise ContractError("Declared dependency inputs required")
    if adapter is None:
        raise DependencyResolutionBlocked(
            ecosystem,
            "no trusted offline resolver adapter/cache is enrolled; lockfile edits remain refused",
        )
    result = adapter.resolve(ecosystem, inputs)
    if type(result) is not dict or result.get("network") is not False:
        raise DependencyResolutionBlocked(
            ecosystem, "adapter did not return an offline resolution"
        )
    return result

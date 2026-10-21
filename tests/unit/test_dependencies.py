"""Dependency resolution stays explicitly blocked without an enrolled adapter."""

import pytest

from hermes_modernisation.dependencies import (
    BLOCKED,
    DependencyResolutionBlocked,
    resolve,
)
from hermes_modernisation.jsonio import ContractError


@pytest.mark.parametrize("ecosystem", ["npm", "pip", "uv"])
def test_default_resolution_is_blocked_without_launching_anything(ecosystem, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Blocked resolution must not launch a resolver")

    monkeypatch.setattr("subprocess.run", forbidden)
    with pytest.raises(DependencyResolutionBlocked) as caught:
        resolve(ecosystem, {"manifest": "declared"})
    assert caught.value.code == BLOCKED
    assert caught.value.execution_performed is False


def test_unknown_ecosystem_and_empty_inputs_are_refused():
    with pytest.raises(ContractError, match="ecosystem"):
        resolve("cargo", {"manifest": "x"})
    with pytest.raises(ContractError, match="inputs"):
        resolve("npm", {})


def test_only_an_offline_adapter_can_return_a_resolution():
    class Adapter:
        def resolve(self, ecosystem, inputs):
            return {"network": True}

    with pytest.raises(DependencyResolutionBlocked, match="offline"):
        resolve("uv", {"manifest": "x"}, adapter=Adapter())

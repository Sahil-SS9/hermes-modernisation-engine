"""Native directory-plugin entrypoint. Inert until the host calls register."""

import importlib
import importlib.util
import sys
from pathlib import Path


def register(ctx):
    root = Path(__file__).parent / "src/hermes_modernisation"
    name = __name__ + "._core"
    spec = importlib.util.spec_from_file_location(
        name, root / "__init__.py", submodule_search_locations=[str(root)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Domain package unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    adapter = importlib.import_module(name + ".adapters.hermes")
    adapter.register(ctx)

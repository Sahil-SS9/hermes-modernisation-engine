"""Native directory-plugin entrypoint. No work or host mutation at import."""
import importlib.util
from pathlib import Path


def register(ctx):
    # Directory distribution only: load the standalone adapter without mutating
    # sys.path or assuming package installation into the host environment.
    path = Path(__file__).parent/'src/hermes_modernisation/adapters/hermes.py'
    spec = importlib.util.spec_from_file_location(__name__+'._adapter', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Modernisation adapter unavailable')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    adapter.register(ctx)

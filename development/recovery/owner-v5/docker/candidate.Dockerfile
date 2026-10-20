# trial-v5 candidate image: the engine recipe-applied pyproject + replayed lock,
# synced fresh inside a container on the Python 3.14 validator base.
# Build network (owner-approved scope): base image pull by pinned digest + PyPI
# downloads during `uv sync`. No host installs; nothing runs here beyond probes.
FROM modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6
WORKDIR /candidate
COPY pyproject.toml README.md uv.lock /candidate/
RUN UV_PROJECT_ENVIRONMENT=/candidate/.venv uv sync --locked --no-install-project --extra dashboard --no-cache
RUN /candidate/.venv/bin/python -c 'import sys,fastapi,httpx,pytest;print("VERSIONS",sys.version.split()[0],fastapi.__version__,httpx.__version__,pytest.__version__)'

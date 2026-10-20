# trial-v5 baseline image: the pinned bdbc723 lock, synced fresh inside a container.
# Build network (owner-approved scope): base image pull by pinned digest + PyPI
# downloads during `uv sync`. No host installs; nothing runs here beyond probes.
FROM python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
WORKDIR /baseline
COPY pyproject.toml README.md uv.lock /baseline/
COPY --from=modernise-validator-fixed@sha256:a947dae20c8ec37ff157da73edb6e98477db536387ba1a10d867b1b7151f66e6 /usr/local/bin/uv /usr/local/bin/uv
RUN UV_PROJECT_ENVIRONMENT=/baseline/.venv uv sync --locked --no-install-project --extra dashboard --no-cache
RUN /baseline/.venv/bin/python -c 'import sys,fastapi,httpx,pytest;print("VERSIONS",sys.version.split()[0],fastapi.__version__,httpx.__version__,pytest.__version__)'

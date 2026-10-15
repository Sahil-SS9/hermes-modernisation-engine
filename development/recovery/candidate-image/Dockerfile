FROM modernise-validator-fixed:local
WORKDIR /candidate
COPY pyproject.toml README.md uv.lock /candidate/
RUN UV_PROJECT_ENVIRONMENT=/candidate/.venv uv sync --locked --no-install-project --extra dashboard --no-cache
RUN /candidate/.venv/bin/python -c "import sys,fastapi,httpx,pytest;print(sys.version);print(fastapi.__version__,httpx.__version__,pytest.__version__)"

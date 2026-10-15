FROM python@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83
RUN python -m pip install --no-cache-dir --only-binary=:all: uv==0.11.28
COPY host-src /opt/hermes
WORKDIR /opt/hermes
RUN uv sync --locked --group dev --group test
RUN uv pip freeze --python /opt/hermes/.venv/bin/python > /host-dependency-manifest.txt
ENV PATH=/opt/hermes/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1

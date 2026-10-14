FROM python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
RUN python -m pip install --no-cache-dir --only-binary=:all: cryptography==46.0.3 pytest==8.4.2 hypothesis==6.135.3 httpx==0.27.2 pytest-asyncio==0.24.0 websockets==14.1 ruff==0.12.10 build==1.3.0 fastapi==0.115.6
RUN python -m pip freeze > /dependency-manifest.txt
ENV PYTHONDONTWRITEBYTECODE=1

# Plan NUC-01, D6: dependencies locked by uv.lock; one Dockerfile, two stages.
#   dev:     everything in uv.lock (dev group included); used by the `dev` service and the hx.
#   runtime: no dev group; used by the `api` service.
# The virtual environment lives outside /app, because the `dev` service bind-mounts the
# repository on /app. The project itself is not installed: PYTHONPATH points to /app/src.

FROM python:3.14.10-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d /uv /uvx /bin/

# UV_COMPILE_BYTECODE: `uv sync` writes the .pyc of every dependency at build time (issue #93,
# plan D1). Without it each Python process recompiled SQLAlchemy, alembic and psycopg (~2.5 s);
# PYTHONDONTWRITEBYTECODE still keeps the bind-mounted repository free of __pycache__.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app


FROM base AS dev

# git: the WEB-01 tests check which files are versioned (`git ls-files`).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Plan WEB-01, D1: Node 24 (copied from the official image by digest, like uv) and pnpm at an
# exact version. Keep the Node version equal to web/package.json (engines) and web/.nvmrc.
# The npm cache is only for installing pnpm; the pnpm store is set below for any --user.
COPY --from=node:24.22.3-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0 /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24.22.3-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0 /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g pnpm@12.23.0 \
    && rm -rf /root/.npm
# `docker compose run --user uid:gid` has no HOME: send the XDG dirs (used by Node tools) to
# /tmp. HOME and CI are NOT set, so pytest and ruff behave as before.
# The pnpm store lives in the `web-node-modules` volume (docker-compose.yml, issue #93): same
# disk as node_modules, kept between runs. pnpm 12 reads only `pnpm_config_*` (the old
# `npm_config_store_dir` was ignored and the store went to /app/.pnpm-store, in the repository).
ENV pnpm_config_store_dir=/app/web/node_modules/.pnpm-store \
    XDG_CACHE_HOME=/tmp/.cache \
    XDG_DATA_HOME=/tmp/.local/share \
    XDG_STATE_HOME=/tmp/.local/state
# Mount point of the volume. A new volume copies this folder's mode, so it is writable by the
# `--user uid:gid` the hx uses on Linux (tested with --user 1000:1000 on 27/11/2026).
RUN mkdir -p /app/web/node_modules && chmod 0777 /app/web/node_modules

# --locked: the build fails if uv.lock is out of date with pyproject.toml.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project


FROM base AS runtime

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project --no-dev

RUN useradd --system --no-create-home --uid 10001 lastro

COPY src/ ./src/
COPY alembic.ini ./
COPY migrations/ ./migrations/

USER lastro

EXPOSE 8000

CMD ["uvicorn", "lastro.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

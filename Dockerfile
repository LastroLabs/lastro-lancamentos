# Plan NUC-01, D6: dependencies locked by uv.lock; one Dockerfile, two stages.
#   dev:     everything in uv.lock (dev group included); used by the `dev` service and the hx.
#   runtime: no dev group; used by the `api` service.
# The virtual environment lives outside /app, because the `dev` service bind-mounts the
# repository on /app. The project itself is not installed: PYTHONPATH points to /app/src.

FROM python:3.14.10-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app


FROM base AS dev

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

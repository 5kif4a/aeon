# syntax=docker/dockerfile:1.7
# Backend image used both for local docker-compose and Railway.
# The frontend is a separate deployment (Vercel) / dev server (Vite).

# --- Stage 1: resolve dependencies into a virtualenv ---
FROM python:3.12.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.10.3 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer is rebuilt only when the lockfile changes.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Stage 2: runtime without uv and build leftovers ---
FROM python:3.12.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv .venv
COPY --chown=app:app backend/alembic.ini ./
COPY --chown=app:app backend/migrations ./migrations
COPY --chown=app:app backend/scripts ./scripts
COPY --chown=app:app backend/app ./app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/api/health\", timeout=2)" || exit 1

# exec keeps uvicorn as PID 1 so SIGTERM reaches it directly
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

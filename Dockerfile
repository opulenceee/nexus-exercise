# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Base stage: Python 3.12 (pinned for reproducibility — host may run newer),
# a virtualenv, and the RUNTIME dependencies.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# postgresql-client gives us `pg_isready` for the entrypoint's wait-for-db loop.
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"

# Dependencies are copied/installed before the app code so this layer is cached
# and only re-runs when requirements change.
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Runtime stage: lean production image (runtime deps only), non-root user.
# ---------------------------------------------------------------------------
FROM base AS runtime
COPY . .
RUN chmod +x entrypoint.sh \
 && adduser --disabled-password --gecos "" appuser \
 && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]

# ---------------------------------------------------------------------------
# Dev stage: adds test/lint deps so `pytest` runs inside the container.
# docker-compose builds this target.
# ---------------------------------------------------------------------------
FROM base AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
RUN chmod +x entrypoint.sh \
 && adduser --disabled-password --gecos "" appuser \
 && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]

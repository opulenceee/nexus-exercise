#!/usr/bin/env bash
# Container entrypoint: wait for Postgres, run migrations, optionally seed,
# then start the API server.
set -euo pipefail

DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" >/dev/null 2>&1; do
  sleep 1
done
echo "Postgres is ready."

# Apply schema migrations (no-op until the first migration exists).
alembic upgrade head

# Idempotent demo seed (skipped unless SEED_ON_START=true and seed.py exists).
if [ "${SEED_ON_START:-false}" = "true" ] && [ -f seed.py ]; then
  python -m seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be configured}"
: "${JWT_SECRET:?JWT_SECRET must be configured}"

alembic upgrade head
exec gunicorn --bind "${HOST:-0.0.0.0}:${PORT:-8000}" --workers "${GUNICORN_WORKERS:-2}" --threads "${GUNICORN_THREADS:-4}" --access-logfile - --error-logfile - "app.main:create_app()"

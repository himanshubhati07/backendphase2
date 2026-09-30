#!/bin/sh
set -eu
python -m app.database.migrate
exec gunicorn --bind "${HOST:-0.0.0.0}:${PORT:-8000}" 'app:create_app()'

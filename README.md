# Story Learning API

Production-oriented Django REST API for early-learning stories, user favorites, completion tracking, and activities.

## Stack

- Python 3.13, Django 5.1, Django REST Framework
- MySQL 8.4.3 in Docker (PyMySQL driver)
- Stateless JWT Bearer access tokens (30-minute default; no refresh or logout)
- drf-spectacular OpenAPI 3 + Swagger UI

## Run locally

```sh
cp .env.example .env
# Set non-placeholder DJANGO_SECRET_KEY, MYSQL_PASSWORD, and MYSQL_ROOT_PASSWORD.
docker compose --env-file .env up --build
```

The web service runs migrations before Gunicorn starts. Browse Swagger at `http://localhost:8000/docs`, the JSON schema at `http://localhost:8000/openapi.json`, and readiness at `http://localhost:8000/health`.

For an isolated local test database without MySQL:

```sh
DJANGO_USE_SQLITE=true python manage.py migrate
DJANGO_USE_SQLITE=true python manage.py seed_stories
DJANGO_USE_SQLITE=true pytest
```

## API conventions

All business routes are under `/api/v1`. Successful responses have:

```json
{"success": true, "message": "...", "data": {}}
```

Errors contain `success: false`, a safe `message`, `error_code`, `details`, `timestamp`, and `request_id`. Send an optional `X-Request-ID` to correlate logs and responses.

Protected routes accept `Authorization: Bearer <access-token>`. Register with `POST /api/v1/auth/register` or sign in with `POST /api/v1/auth/login`.

Collection endpoints use native DRF limit-offset pagination: `?limit=20&offset=0` (maximum limit 100). Public catalog routes expose active stories only.

## Seed content

`python manage.py seed_stories` is idempotent and creates eight categories and ten active English stories for ages `2-3`, including *The Little Bunny*, *Colors Around Us*, *Five Little Ducks*, *My First Shapes*, and *Good Mornin*.

## Tests

```sh
DJANGO_USE_SQLITE=true pytest
DJANGO_USE_SQLITE=true python manage.py check
```

The test suite covers auth, envelopes, public catalog querying, validation, authorization, favorites, progress idempotency, activity operations, pagination, and ownership isolation.

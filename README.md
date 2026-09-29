# Gym API

A synchronous Bottle/SQLAlchemy API for gym members, trainers, memberships, attendance, payments, and workout plans. The service is WSGI-ready and uses MySQL in production. SQLite is supported for isolated local and test databases.

## Requirements

- Python 3.13 (the container uses `python:3.13.5-slim`)
- MySQL 8.0+ for production, or Docker Compose
- A unique high-entropy JWT signing secret

## Configuration

Copy the environment template, replace every placeholder, and keep the resulting `.env` private:

```sh
cp .env.example .env
# Generate a value for JWT_SECRET, for example:
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | yes | SQLAlchemy URL; `mysql://...` is accepted and converted to PyMySQL. |
| `JWT_SECRET` | yes | Per-environment HS256 signing secret. Never commit it. |
| `JWT_ISSUER` | no | JWT issuer, default `gym-api`. |
| `JWT_ACCESS_TTL_SECONDS` | no | Access-token lifetime, default `900`. |
| `JWT_REFRESH_TTL_SECONDS` | no | Refresh-token lifetime, default `604800`. |
| `APP_ENV` | no | Deployment label, default `production`. |
| `CORS_ORIGINS` | no | Comma-separated explicit allowed origins. |
| `LOG_LEVEL` | no | Python log level, default `INFO`. |
| `GUNICORN_WORKERS`, `GUNICORN_THREADS` | no | Gunicorn process/thread counts. |

`JWT_ACCESS_TOKEN_MINUTES` and `JWT_REFRESH_TOKEN_DAYS` remain accepted only for backwards compatibility; prefer the TTL-in-seconds variables above. Docker Compose additionally reads `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_ROOT_PASSWORD` to initialize MySQL.

## Local setup

```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DATABASE_URL='sqlite:///gym.db'
alembic upgrade head
gunicorn --bind 0.0.0.0:8000 'app.main:create_app()'
```

The health endpoint is `GET /health` (also available at `/api/health`). The OpenAPI document is served at `GET /api/openapi.json` in the API response envelope.

## Docker Compose

1. Create and complete `.env` from `.env.example`; do not use placeholder values.
2. Start the generated API image and pinned MySQL service:

```sh
docker compose up --build
```

The `mysql:8.0.40` service is health-checked before `api` starts. The API startup command runs `alembic upgrade head` and then Gunicorn. The database volume is named `mysql_data`; remove it only when intentionally discarding data:

```sh
docker compose down -v
```

## Migrations

Alembic owns schema changes. The initial revision creates all domain tables, constraints, indexes, and foreign keys in dependency-safe order.

```sh
# Apply all migrations
DATABASE_URL='mysql://user:password@host:3306/gym_api?charset=utf8mb4' alembic upgrade head

# Show current schema revision
alembic current

# Roll back one revision (destructive for the initial revision)
alembic downgrade -1

# Generate a candidate after intentionally changing models; inspect it before committing
alembic revision --autogenerate -m 'describe schema change'
```

Do not call `Base.metadata.create_all()` in production and do not modify an applied migration. Back up production databases and test both upgrade and downgrade paths before release.

## Authentication and security

- Passwords are bcrypt hashes; plaintext passwords are not stored.
- Tokens are signed HS256 JWTs with issuer, subject, role, token type, issued-at, and expiry claims.
- Use `Authorization: Bearer <access_token>` on protected routes. Refresh tokens are accepted only at the refresh endpoint.
- Access lifetimes are intentionally short; protect refresh tokens like passwords and rotate `JWT_SECRET` using a coordinated deployment.
- Roles are `admin`, `trainer`, and `member`; server-side RBAC and ownership checks are applied per route.
- Set `CORS_ORIGINS` to known HTTPS frontend origins rather than `*`. Responses set conservative browser security headers and avoid logging credentials or request bodies.
- Use unique database credentials with least privilege, TLS for external MySQL connections, backups, dependency updates, and a managed secret store in production.

## API surface

All responses use `success`, `message`, and either `data` or `error_code` fields. JSON requests should send `Content-Type: application/json`.

| Area | Endpoints |
| --- | --- |
| System | `GET /health`, `GET /api/health`, `GET /api/openapi.json` |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` |
| Members | `POST, GET /api/members`; `GET, PUT, DELETE /api/members/{member_id}` |
| Trainers | `POST, GET /api/trainers`; `GET, PUT, DELETE /api/trainers/{trainer_id}`; `PUT /api/trainers/{trainer_id}/members/{member_id}` |
| Plans | `GET, POST /api/plans`; `GET, PUT, PATCH /api/plans/{plan_id}`; `POST /api/plans/{plan_id}/deactivate` |
| Memberships | `POST /api/members/{member_id}/memberships`; `GET /api/members/{member_id}/memberships/active`; `GET /api/members/{member_id}/memberships/history`; `POST /api/memberships/{membership_id}/renew`, `.../cancel` |
| Attendance | `POST /api/attendance/check-in`; `POST /api/attendance/{attendance_id}/check-out`; `GET /api/attendance`, `/api/attendance/daily`, `/api/members/{member_id}/attendance` |
| Payments | `POST, GET /api/payments`; `GET /api/payments/{payment_id}`; `PATCH /api/payments/{payment_id}/status`; `GET /api/members/{member_id}/payments` |
| Workouts | `POST /api/workout-plans`; `PUT, DELETE /api/workout-plans/{plan_id}`; `PUT /api/workout-plans/{plan_id}/members/{member_id}`; `GET /api/members/{member_id}/workout-plans` |

## Testing

Use a temporary SQLite database and a test-only JWT secret. Never point tests at production.

```sh
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DATABASE_URL='sqlite:///'
pytest -q
```

`pytest` and `WebTest` are included for HTTP-level tests. `openpyxl` and `python-docx` are available for spreadsheet and document export test coverage. Run migration checks independently when changing schema:

```sh
DATABASE_URL='sqlite:///migration-test.db' alembic upgrade head
DATABASE_URL='sqlite:///migration-test.db' alembic downgrade base
```

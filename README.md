# Employee Management System

A monolithic Spring Boot REST API for managing employee records, secured with JWT
authentication. Built with Java 21, Spring Boot 3.2.10, Gradle 8.11.1, JPA/Hibernate
6.2.24, and PostgreSQL 17.2, with Flyway-managed migrations.

## Tech stack

| Concern | Choice |
|---|---|
| Language | Java 21 |
| Framework | Spring Boot 3.2.10 |
| Build tool | Gradle 8.11.1 |
| ORM | JPA / Hibernate 6.2.24 |
| Database | PostgreSQL 17.2 |
| Migrations | Flyway |
| Auth | JWT (HS256), 30-minute access tokens, no refresh tokens, no RBAC |
| API docs | springdoc-openapi, Swagger UI at `/docs` |
| Testing | curl scripts under `tests/` (no JUnit suite) |

## Project layout

```
src/main/java/com/ems/
  config/       Spring configuration (security, OpenAPI, WebSocket)
  controller/   Thin REST controllers
  dto/          Request/response DTOs and envelopes (never expose entities directly)
  entity/       JPA entities
  exception/    Domain exceptions + centralized @RestControllerAdvice handler
  repository/   Spring Data JPA repositories
  security/     JWT issuance/validation, auth filter, entry point / access-denied handler
  service/      Business logic
  websocket/    WebSocket scaffold
src/main/resources/
  application.yml, application-dev.yml
  db/migration/V1__init.sql   Flyway schema
tests/           curl-based API test scripts (see "Testing" below)
```

## Environment variables

Copy `.env.example` to `.env` and fill in real values before running anything that
isn't purely local development:

| Variable | Purpose | Example |
|---|---|---|
| `DB_URL` | JDBC URL for PostgreSQL | `jdbc:postgresql://localhost:5432/ems` |
| `DB_USERNAME` | Database user | `ems` |
| `DB_PASSWORD` | Database password | *(secret)* |
| `POSTGRES_DB` | DB name created by the `db` compose service | `ems` |
| `JWT_SECRET` | HMAC signing secret for JWTs (any length - it's stretched to 256 bits internally) | *(secret)* |
| `SPRING_PROFILES_ACTIVE` | Active Spring profile (`dev` locally, unset/`default` otherwise) | `dev` |

No secret ever has a real value committed to source control; `application.yml` only
contains safe local-dev fallbacks.

## Running with Docker Compose (recommended)

```bash
cp .env.example .env    # edit values as needed
make docker-up          # docker compose up -d --build
```

This starts PostgreSQL 17.2 and the application (port `8080`), waiting for the
database's healthcheck before starting the app. Flyway migrations run automatically
on startup.

Tear down with:

```bash
make docker-down
```

## Running locally with Gradle

Requires a local or remote PostgreSQL 17.2 instance reachable via `DB_URL`.

```bash
export DB_URL=jdbc:postgresql://localhost:5432/ems
export DB_USERNAME=ems
export DB_PASSWORD=ems_password
export JWT_SECRET=some-long-random-value
export SPRING_PROFILES_ACTIVE=dev

make build   # ./gradlew clean bootJar -x test
make run     # ./gradlew bootRun
```

## API documentation

- Swagger UI: `GET /docs`
- OpenAPI spec (JSON): `GET /api-docs`
- Health check (no auth): `GET /health`

Every endpoint below is also documented there with full request/response schemas.

## API reference & curl examples

All business endpoints are prefixed with `/api/v1`. All responses are wrapped in a
`{success, message, data}` envelope. List/search endpoints additionally wrap their
page in `{content, page, limit, totalElements, totalPages}`.

### Auth (public)

**Register**
```bash
curl -i -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"SuperSecret123"}'
```
Returns `201` with `{accessToken, tokenType, expiresInSeconds}`, or `409` if the email
is already registered.

**Login**
```bash
curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"SuperSecret123"}'
```
Returns `200` with `{accessToken, tokenType, expiresInSeconds}`, or `401` on bad
credentials. Save `accessToken` and send it as `Authorization: Bearer <token>` on every
employee endpoint below.

### Employees (JWT-protected)

**Create**
```bash
curl -i -X POST http://localhost:8080/api/v1/employees \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"firstName":"Jane","lastName":"Doe","email":"jane.doe@example.com","phone":"555-0100","department":"Engineering","designation":"Software Engineer","salary":95000.00,"joiningDate":"2024-01-15","status":"ACTIVE"}'
```
`201` on success, `409` if the email is already in use, `400` on validation failure.

**Get by id**
```bash
curl -i http://localhost:8080/api/v1/employees/1 -H "Authorization: Bearer $TOKEN"
```
`200`, or `404` if not found.

**List (offset-paginated)**
```bash
curl -i "http://localhost:8080/api/v1/employees?page=0&limit=20" -H "Authorization: Bearer $TOKEN"
```

**Update**
```bash
curl -i -X PUT http://localhost:8080/api/v1/employees/1 \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"firstName":"Jane","lastName":"Doe","email":"jane.doe.updated@example.com","department":"Engineering","designation":"Senior Software Engineer","salary":110000.00,"joiningDate":"2024-01-15","status":"ACTIVE"}'
```
`200`, `404` if not found, `409` if the new email collides with another employee.

**Delete**
```bash
curl -i -X DELETE http://localhost:8080/api/v1/employees/1 -H "Authorization: Bearer $TOKEN"
```
`204 No Content` on success, `404` if not found.

**Search**
```bash
curl -i -G "http://localhost:8080/api/v1/employees/search" \
  --data-urlencode "department=Engineering" --data-urlencode "page=0" --data-urlencode "limit=20" \
  -H "Authorization: Bearer $TOKEN"
```
Query params: `name` (matches first or last name), `email`, `department` - all
optional, case-insensitive, plus `page`/`limit`.

**Missing/invalid token**
```bash
curl -i http://localhost:8080/api/v1/employees                                   # 401, no header
curl -i http://localhost:8080/api/v1/employees -H "Authorization: Bearer garbage" # 401, bad token
```

## Testing

No JUnit suite is generated for this project; verification is via the curl scripts in
`tests/`:

```bash
make test                         # runs tests/run_all.sh against $BASE_URL (default localhost:8080)
BASE_URL=http://localhost:8080 bash tests/run_all.sh
```

`tests/run_all.sh` exercises the full flow end-to-end (register -> login -> employee
CRUD -> search -> pagination -> invalid token -> missing resource) with pass/fail
assertions on HTTP status codes. The numbered scripts (`01_register.sh` ...
`10_missing_resource.sh`) are standalone, documented examples of each endpoint for
manual use.

## WebSocket scaffold

`GET /ws/notifications` - a raw WebSocket endpoint (`NotificationWebSocketHandler`)
that currently just echoes received text frames and logs connection lifecycle events.
No employee business logic is wired to it yet; it exists so future event-driven
features (e.g. "notify on new hire") don't require a structural rewrite.

## Database schema & migrations

Flyway migration `V1__init.sql` creates the `users` and `employees` tables (see
`src/main/resources/db/migration/`) with unique constraints on both tables' `email`
columns and indexes on `employees(department)`, `employees(email)`, and
`employees(last_name, first_name)`. Migrations run automatically on every application
startup; `make migrate` runs them standalone (useful before a first boot) via the
official Flyway CLI Docker image.

## CI

`.github/workflows/ci.yml` builds the project with Gradle against a real PostgreSQL
17.2 service container on every push/PR, and boots the app briefly to confirm Flyway
migrations apply cleanly.

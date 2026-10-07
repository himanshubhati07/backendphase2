# Checkpoint

## Decisions
- Stack: Python 3.13.5, FastAPI 0.115.6, PostgreSQL 17.2, psycopg connection pooling, JWT bearer (HS256, 30 minutes).
- API: `/api/v1`; REST success/error envelopes; correlation IDs; `/health`, built-in `/docs` and `/openapi.json`.
- Entities: `users(id, email normalized unique, password_hash, created_at)` owns `tasks(id, user_id, title, description, priority, due_date, status, created_at, updated_at)`.
- Resource groups: Auth owns users/auth endpoints/security/dependency contracts; Tasks owns task schemas/service/repository/routes. Shared contract: `CurrentUser(id:int,email:str)`, repositories receive psycopg connections, enums exact values in specification.
- Port: 8000. Frontend is static assets served by FastAPI. Docker Compose services: `app`, `db` (`postgres:17.2`).

## Status
- [x] STEP 1 design and endpoint testability classification (all specified endpoints testable)
- [x] STEP 2–8 implementation (database, schemas, auth, task API, static frontend, Docker and tests)
- [x] STEP 9 README
- [x] STEP 10 syntax/import check (`compileall`; OpenAPI import check passed)
- [x] STEP 11 pytest attempted; blocked by unavailable Docker/Compose PostgreSQL (`db` hostname resolution / pool timeout)
- [x] STEP 14 boot attempted; first of three attempts timed out while DB was unavailable; Docker daemon/Compose plugin unavailable
- [x] STEP 15 reports (`tests-artifacts/api_test_report.xlsx`, `tests-artifacts/project_report.docx`) with observed failures
- [x] STEP 16 delivery checks: Dockerfile and docker-compose.yml exist; Docker pull/build/run unavailable on this host

## Auth/User Unit Status
- [x] Auth/user feature implemented: bcrypt password hashing, HS256 access-token creation/validation, parameterized user repository, bearer current-user dependency, and `/api/v1/auth/register` plus `/api/v1/auth/login` routes.
- Assumption: the parent application imports `app.routes_auth.router` and installs the existing exception handlers/database lifecycle. No tests run per unit instruction.

## Tasks feature unit
- [x] Added owner-scoped task repository, service, and authenticated routes for create, list, retrieve, replace, complete, and delete. List filtering/pagination uses a separate matching count query; all task-ID mutations and retrievals are owner constrained.

## Integration test unit
- [x] Added PostgreSQL-backed pytest fixtures plus auth and task route integration tests. Fixtures source `TEST_DATABASE_URL`, initialize the application schema, truncate tables for each test, and exercise real FastAPI/JWT dependencies. Tests were not executed because `app.main:app` is designated to be added by another unit.

## Frontend unit
- [x] Added same-origin static SPA assets with accessible registration/login, in-memory bearer JWT handling, protected task dashboard/detail/create/edit UI, task filtering, offset pagination, completion, deletion, and responsive styles.

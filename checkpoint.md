# Checkpoint

## Decisions
- Stack: Python 3.13.5, FastAPI 0.115.6, PostgreSQL 17.2, psycopg connection pooling, JWT bearer (HS256, 30 minutes).
- API: `/api/v1`; REST success/error envelopes; correlation IDs; `/health`, built-in `/docs` and `/openapi.json`.
- Entities: `users(id, email normalized unique, password_hash, created_at)` owns `tasks(id, user_id, title, description, priority, due_date, status, created_at, updated_at)`.
- Resource groups: Auth owns users/auth endpoints/security/dependency contracts; Tasks owns task schemas/service/repository/routes. Shared contract: `CurrentUser(id:int,email:str)`, repositories receive psycopg connections, enums exact values in specification.
- Port: 8000. Frontend is static assets served by FastAPI. Docker Compose services: `app`, `db` (`postgres:17.2`).
- Remediation design: all deployment secrets/connection strings are required environment variables; `.env.example` documents safe values. Compose provisions a separate `task_manager_test` database, and tests require `TEST_DATABASE_URL` distinct from `DATABASE_URL`. API error documentation uses the existing `ErrorResponse` envelope for 401/404/409/422/500. JWT encode/decode use `Settings.jwt_algorithm`.

## Status
- [x] STEP 1 design and endpoint testability classification (all specified endpoints testable)
- [x] STEP 2–8 implementation (database, schemas, auth, task API, static frontend, Docker and tests)
- [x] STEP 9 README
- [x] STEP 10 syntax/import check (`compileall`; OpenAPI import check passed before remediation)
- [ ] STEP 11 pytest: still not executed successfully. Docker daemon cannot start in this sandbox (cgroup mount permission errors); the PostgreSQL-backed suite remains pending.
- [ ] STEP 14 boot: not successful. Docker Compose is unavailable (`unknown shorthand flag: 'd' in -d`) and the installed daemon cannot start due cgroup permissions.
- [ ] STEP 15 reports: existing XLSX/DOCX record prior failed observations; required real-pass `test_results.json` has not been generated because no live app/database test run occurred.
- [ ] STEP 16 Docker deployment verification: not successful. Image pull/build/run is blocked by the sandbox Docker daemon/cgroup restriction.
- [x] Verifier remediation: `app/repositories.py` now provides and is actively used through `UserRepository` and `TaskRepository`; legacy function modules are compatibility wrappers.
- [ ] Verifier remediation: rerun PostgreSQL pytest, live HTTP report generation, and Compose deployment verification on the currently available Docker runner.

## Auth/User Unit Status
- [x] Auth/user feature implemented: bcrypt password hashing, HS256 access-token creation/validation, parameterized user repository, bearer current-user dependency, and `/api/v1/auth/register` plus `/api/v1/auth/login` routes.
- Assumption: the parent application imports `app.routes_auth.router` and installs the existing exception handlers/database lifecycle. No tests run per unit instruction.

## Tasks feature unit
- [x] Added owner-scoped task repository, service, and authenticated routes for create, list, retrieve, replace, complete, and delete. List filtering/pagination uses a separate matching count query; all task-ID mutations and retrievals are owner constrained.

## Integration test unit
- [x] Added PostgreSQL-backed pytest fixtures plus auth and task route integration tests. Fixtures source `TEST_DATABASE_URL`, initialize the application schema, truncate tables for each test, and exercise real FastAPI/JWT dependencies. Tests were not executed because `app.main:app` is designated to be added by another unit.

## Frontend unit
- [x] Added same-origin static SPA assets with accessible registration/login, in-memory bearer JWT handling, protected task dashboard/detail/create/edit UI, task filtering, offset pagination, completion, deletion, and responsive styles.

## PostgreSQL test/deployment configuration remediation
- [x] Made Compose database and application runtime settings environment-required; added documented nonproduction `.env.example` values.
- [x] Mounted PostgreSQL initialization SQL to create the dedicated `task_manager_test` database alongside `task_manager`.
- [x] Updated integration fixtures to require and validate a distinct `TEST_DATABASE_URL` before configuring or truncating the test database.

## Tasks OpenAPI documentation remediation
- [x] Documented `ErrorResponse` for protected task-route 401s, task-ID 404s, validation 422s, and 500s through FastAPI `responses` metadata without changing task endpoint behavior or success models.

## Auth/config remediation unit
- [x] `DATABASE_URL` and `JWT_SECRET` are required `Settings` inputs with no source defaults; JWT signing and verification share configurable `jwt_algorithm` (default `HS256`); auth OpenAPI documents ErrorResponse models for required error statuses.

## Verification blocker (current run)
- Docker pull failed because the original daemon was unavailable. Installing Docker Engine did not resolve it: daemon startup fails with `mount: /sys/fs/cgroup/cpu: permission denied` and Docker remains unreachable. The installed CLI also has no Compose plugin; `docker compose up -d db` reports `unknown shorthand flag: 'd' in -d`.
- Consequently, no PASS rows or `test_results.json` were fabricated. A functional Docker-capable runner is still required to run the isolated PostgreSQL pytest suite, boot the service, capture real HTTP report rows (including `/docs` and `/openapi.json`), generate reports, and run final image verification.

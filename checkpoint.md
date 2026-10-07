# Checkpoint

## Decisions
- Stack: Python 3.13.5, FastAPI 0.115.6, PostgreSQL 17.2, psycopg connection pooling, JWT bearer (HS256, 30 minutes).
- API: `/api/v1`; REST success/error envelopes; correlation IDs; `/health`, built-in `/docs` and `/openapi.json`.
- Entities: `users(id, email normalized unique, password_hash, created_at)` owns `tasks(id, user_id, title, description, priority, due_date, status, created_at, updated_at)`.
- Resource groups: Auth owns users/auth endpoints/security/dependency contracts; Tasks owns task schemas/service/repository/routes. Shared contract: `CurrentUser(id:int,email:str)`, repositories receive psycopg connections, enums exact values in specification.
- Port: 8000. Frontend is static assets served by FastAPI. Docker Compose services: `app`, `db` (`postgres:17.2`).

## Status
- [x] STEP 1 design and endpoint testability classification (all specified endpoints testable)
- [ ] STEP 2–8 implementation
- [ ] STEP 9 README
- [ ] STEP 10–14 verification and fixes
- [ ] STEP 15 reports
- [ ] STEP 16 final verification

## Auth/User Unit Status
- [x] Auth/user feature implemented: bcrypt password hashing, HS256 access-token creation/validation, parameterized user repository, bearer current-user dependency, and `/api/v1/auth/register` plus `/api/v1/auth/login` routes.
- Assumption: the parent application imports `app.routes_auth.router` and installs the existing exception handlers/database lifecycle. No tests run per unit instruction.

## Tasks feature unit
- [x] Added owner-scoped task repository, service, and authenticated routes for create, list, retrieve, replace, complete, and delete. List filtering/pagination uses a separate matching count query; all task-ID mutations and retrievals are owner constrained.

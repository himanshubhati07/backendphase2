# Checkpoint

## Design
- Mode: greenfield Bottle 0.13.2, Python 3.13.5, synchronous SQLAlchemy, Alembic, MySQL production / SQLite test fixtures.
- Single service `gym-api`, port 8000; Docker Compose services: `api` and `mysql` (MySQL 8.0.40).
- Package convention: `app/` contains config, database, models, validation/auth/error helpers, route modules, and WSGI app factory. All API response envelopes are exact `success/message/data` or `success/message/error_code`.
- RBAC contract: admin all; trainer manages own profile, assigned members and their attendance/memberships/workouts; member sees self resources. Public registration may make member or trainer profiles, never admin.
- Entity-group ownership: Core/Auth (config/database/models/security/auth/openapi); Members/Trainers; Memberships/Attendance; Payments/Workouts. Shared model names and HTTP paths follow the supplied specification.

## Status
- [x] STEP 1 design/scaffold decisions
- [x] Core/Auth foundation — Bottle factory, immutable settings, sync SQLAlchemy schema/models, response/error/validation utilities, JWT/bcrypt RBAC, auth/health/OpenAPI routes
- [x] Members/Trainers feature group — normalized contact/profile schema, registration compatibility, protected member/trainer CRUD, deactivation, search, and active trainer assignment implemented
- [x] Memberships/Attendance feature group — protected plan/membership lifecycle and attendance check-in/out/history/report routes implemented
- [x] Payments/Workouts feature group — payment and workout routes wired; secure payment schema/validation, RBAC-scoped queries, atomic exercise replacement, and cascading exercises implemented.
- [x] Contract reconciliation and OpenAPI expansion — full route inventory and bearer/error schemas documented
- [x] Migration, documentation, container deliverables — initial Alembic revision, README, environment example, Gunicorn start script, Dockerfile, and Compose MySQL/API stack
- [x] Test suite and runtime verification — dependency installation, compile, Alembic SQLite upgrade, pytest (4 passed), Gunicorn health/OpenAPI probe, and live HTTP report generation completed

## Verification evidence
- `python -m pytest -q`: 4 passed.
- `python -m compileall -q app`: passed.
- `DATABASE_URL=sqlite:///./migration-check.db JWT_SECRET=test-secret alembic upgrade head`: passed.
- Gunicorn booted on port 8000 and `/api/health` plus `/api/openapi.json` returned 200; final live-report boot succeeded after one report-script cwd setup failure.
- Live observed-report artifacts: `tests-artifacts/api_test_report.xlsx` and `tests-artifacts/project_report.docx`.
- Docker daemon was unavailable in this environment, so compose/MySQL runtime verification could not be executed; the required Dockerfile and compose file were verified on disk.
- [ ] Migration, documentation, container deliverables
- [ ] Install, migration, lint, tests, boot verification and reports
- [x] Delivery infrastructure — Alembic initial schema migration, container/runtime files, environment template, dependency pins, and operational README added.
- [x] API integration test unit — isolated SQLite/WebTest pytest coverage for auth, membership/attendance, payments, workouts, RBAC, validation, and safe DB-conflict responses

## Verifier remediation contract
- Membership plans are canonically `/api/membership-plans`; membership history is `GET /api/members/{member_id}/memberships`; attendance checkout is `POST /api/attendance/check-out` with `attendance_id` in JSON. Legacy incorrect paths are removed rather than documented.
- `MembershipPlan.features` is JSON and plan status is the `active`/`inactive` enum. `Membership` carries decimal `amount`, `payment_status`, and supports `pending`. `Attendance.check_in_at` is required; incompatible nullable `checked_in_at`, `status`, and notes fields are removed. A follow-on Alembic revision upgrades the original schema.
- Passwords require at least 8 characters and each of uppercase, lowercase, digit, and special character. Safe errors include distinct not-found, conflict, and database-failure classes; unexpected SQLAlchemy failures return a non-leaking `DATABASE_ERROR` 500.
- Remediation in progress: membership/attendance schema/routes/migration and core/auth/error/OpenAPI/production-entrypoint are independent implementation groups; expanded tests and evidence run after both groups complete.
- [x] Verifier remediation implementation — canonical membership/attendance contract and follow-on migration added; password security, safe database exception mapping, explicit OpenAPI, and Gunicorn-only application entrypoint completed.
- [x] Expanded verification, readable evidence, reports and final boot check — `python -m compileall -q app`, SQLite Alembic upgrade through `20250102_0002`, and `python -m pytest -q tests` all passed (7 tests). Temporary SQLite boot through `start.sh`/Gunicorn on port 8012 passed live health, OpenAPI, password, registration, login, identity, token-type rejection, and anonymous-protection probes. `tests-artifacts/test_results.json` now records 17 individually observed checks using the report contract columns; refreshed XLSX/DOCX reports are in `tests-artifacts/`. Docker daemon remained unavailable, so MySQL compose was not started.

## Final remediation evidence
- Canonical public routes are implemented, documented, tested, and OpenAPI-described: `/api/membership-plans`, `GET /api/members/{member_id}/memberships`, and JSON-body `POST /api/attendance/check-out`.
- Follow-on migration `20250102_0002` reconciles plan/membership/attendance persistence fields from initial schema and passed SQLite upgrade verification.
- Production entrypoint no longer invokes Bottle development `run()`; Gunicorn is required by the executable/start-script contract.

## Verifier gap-fix plan
- [x] STEP gap-fix design/scaffold: canonical deactivation is `DELETE /api/membership-plans/{plan_id}`; the legacy POST action is removed. Production configuration requires `DATABASE_URL`; `HOST` and `PORT` are environment-backed and documented. Monetary amounts are decimal non-negative (`>= 0`).
- [x] Core contract group: environment config, redacted structured database logging, and OpenAPI corrections. OpenAPI contracts: registration phone lives exclusively in `profile.phone`; plan `features` accepts object or array JSON; Error responses include `METHOD_NOT_ALLOWED`/405.
- [x] Membership/attendance migration group: membership status deployment contract includes `pending`, plan DELETE deactivation, and attendance requires both an active subscription and member `membership_status == active`.
- [x] Verification group: expanded API/migration security coverage for workouts, payments, zero amounts, CORS/security headers, redaction, and schema upgrade/downgrade; reports regenerated from observed verification.

## Gap-fix decisions
- Migration revision will follow `20250102_0002`, remain SQLite/MySQL compatible, and represent membership-status compatibility without relying on database-native enum alteration (the deployed contract is enforced by the application enum/check-compatible column values and migration schema test).
- Redacted operational logs contain only a fixed event name and request ID; they never attach exceptions, SQL, values, request bodies, headers, card fields, or traceback data for database exceptions.
- Workout scenarios are tested via existing authenticated API flows: trainer creates/replaces exercises and assigns workouts; members retrieve only assigned workouts; unrelated members are denied.

## Core-contract verifier fixes
- [x] Core configuration/logging/OpenAPI/docs: `DATABASE_URL` is mandatory outside explicit `APP_ENV=test`; test mode retains an isolated SQLite default and explicit test URLs remain supported. `HOST`/`PORT` are typed environment settings, passed through Compose/startup, and documented in `.env.example` and README.
- [x] SQLAlchemy/IntegrityError operational events are redacted to a fixed event and request ID without exception objects, SQL, values, or traces; fallback global database/unhandled logging is likewise trace-free while keeping safe response envelopes.
- [x] OpenAPI registration documents phone exclusively at `profile.phone`; membership plan feature inputs are object-or-array JSON; `METHOD_NOT_ALLOWED` and 405 error responses are documented for all operations.
- Verification note: source-level compile/test execution was not available through this unit's filesystem-only tool interface; no tests were changed.

## Membership/attendance verifier fixes
- [x] Replaced the legacy plan-deactivation action with admin-only `DELETE /api/membership-plans/{plan_id}`; no legacy POST route remains.
- [x] Plan prices and membership amounts now permit zero and reject negative/non-finite/out-of-range values.
- [x] Added `20250103_0003`, a SQLite/MySQL-compatible membership-status migration that adds the persisted `PENDING` status check; downgrade maps pending rows to cancelled before restoring the preceding three-state contract.
- [x] Membership assignment/renewal, expiry processing, and cancellation synchronize `Member.membership_status`; attendance check-in requires both that member state and a currently active membership record.
- [x] Parent verification subsequently compiled the application and exercised upgrade/downgrade/re-upgrade through this revision on SQLite.

## Expanded automated coverage (test unit)
- [x] Updated legacy membership-plan deactivation assertions to canonical `DELETE /api/membership-plans/{plan_id}` and its OpenAPI contract.
- [x] Added isolated API/config/security/workout coverage for zero and negative amounts, member pending attendance denial, card-field rejection, response/log redaction, CORS/security headers, HOST/PORT configuration, OpenAPI 405/nested-phone/oneOf details, and trainer/admin workout lifecycle/RBAC scenarios.
- [x] Added an Alembic SQLite revision test that upgrades `20250103_0003`, persists schema-valid `PENDING`, then downgrades and verifies conversion to `CANCELLED`.
- [x] Final verification completed: `python -m compileall -q app` and `python -m pytest -q -vv tests` passed with 15 tests; SQLite Alembic upgraded `20250101_0001 -> 20250103_0003`, downgraded to `20250102_0002`, then re-upgraded successfully.
- [x] Final Gunicorn boot verification succeeded using `start.sh` with explicit test environment on port 8012. The report generator made live `GET /api/health` and `GET /api/openapi.json` requests (both 200) and verified the DELETE plan contract; it then regenerated `tests-artifacts/api_test_report.xlsx`, `project_report.docx`, and accumulated `test_results.json` (25 observed rows).
- Docker daemon was unavailable (`python:3.13-slim` pull could not connect), so compose/MySQL was not run; portable SQLite migration and application verification succeeded.

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
- [ ] Expanded verification, readable evidence, reports and final boot check

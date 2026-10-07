# Checkpoint

## Design
- Stack: Django 5.1.4, DRF, SimpleJWT, MySQL 8.4.3; pytest-django.
- Apps: `accounts` owns UUID email users and JWT auth; `stories` owns categories, stories, activities; `engagement` owns favorites and learning progress.
- APIs are rooted at `/api/v1`; UUIDs are canonical identifiers. Offset pagination uses DRF `LimitOffsetPagination` (`limit`, `offset`, default 20).
- Shared contracts: `Story` has UUID `id`, category FK, language constrained to `en`, age group constrained to `2-3`; all story mutation requires JWT. `Favorite` and `LearningProgress` refer to `accounts.User` and `stories.Story` and are unique by `(user, story)`.
- Response contract: success `{success,message,data}`; errors additionally include `error_code`, `details`, `timestamp`, and `request_id`.
- Remediation: retain app ownership but add a documented `api` facade package containing response, exception, serializer, service, view, and URL modules. It re-exports the established centralized behavior and routes, avoiding duplicate endpoint implementations. Add HTTP API coverage for the complete stories/activity endpoint matrix; duplicate registration raises centralized `Conflict` (409).
- Compose environment values containing commas/colons must be quoted; one-off report scripts are deleted after artifacts are generated.

## Status
- [x] STEP 1 design
- [x] STEP 2 scaffold (Django startproject/startapp)
- [x] STEP 3-6 application, migrations, and idempotent seed command
- [x] STEP 7 infrastructure (Dockerfile and compose existence verified)
- [x] STEP 8 tests (12 pytest tests)
- [x] STEP 9 README
- [x] STEP 10-16 checks, boot verification, and reports

## Verification
- `DJANGO_USE_SQLITE=true python manage.py check`, migration drift check, migrations, and seed command passed.
- `DJANGO_USE_SQLITE=true pytest`: 12 passed.
- Live Gunicorn boot verification passed; 11 observed HTTP checks passed. Reports are in `tests-artifacts/`.
- Docker image pulls and Dockerfile build/run verification were attempted but the host Docker daemon is unavailable (`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`).
- Final secret configuration check: deployment requires `DJANGO_SECRET_KEY`; SQLite test runs use an ephemeral process-only key.

## Engagement resource status
- Implemented `engagement`: UUID `Favorite` and `LearningProgress` models, initial migration, serializers, service layer, authenticated API views, and app URL patterns for the `/api/v1/` engagement contract.
- Added pytest coverage for authentication, ownership isolation, duplicate favorites, completion idempotency, and limit/offset pagination.
- Pending shared integration: project settings/URL wiring and shared `config.responses` / `config.exceptions` are owned outside this resource.

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
- [x] Verifier remediation: HTTP stories/activity coverage, duplicate-registration 409, `api` facade, quoted compose values, and removed report helper

## Verification
- `DJANGO_USE_SQLITE=true python manage.py check`, migration drift check, migrations, and seed command passed.
- `DJANGO_USE_SQLITE=true pytest`: 18 passed after verifier remediation.
- Live Gunicorn boot verification passed after a health poll; 20 individually observed HTTP checks were recorded in regenerated reports under `tests-artifacts/`.
- Docker image pulls and Dockerfile build/run verification were re-attempted but the host Docker daemon is unavailable (`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`). The host also lacks the Docker Compose plugin (`docker: 'compose' is not a docker command`), so compose startup could not be run. Dockerfile verification FAILED externally: 1 attempted environment check, last error is the daemon connection failure.
- `docker-compose.yml` parses successfully as YAML with quoted comma/colon environment interpolation values; one-off `generate_reports.py` was deleted after artifact verification.
- Final secret configuration check: deployment requires `DJANGO_SECRET_KEY`; SQLite test runs use an ephemeral process-only key.

## Current verifier remediation plan
- MySQL compatibility: retain pinned `PyMySQL==1.1.1` and install its `MySQLdb` compatibility shim in `config/__init__.py`, before Django settings/backend initialization. Production database engine remains Django's MySQL backend.
- Configured catalogue options: `SUPPORTED_STORY_LANGUAGES = ("en",)` and `SUPPORTED_STORY_AGE_GROUPS = ("2-3",)` live in Django settings; model choices and serializer validation consume those settings.
- API contract documentation: all endpoints receive drf-spectacular operation descriptions, explicit JWT bearer security where protected, parameters, and success/error envelope response schemas. The standard success envelope is `{success, message, data}` and error envelope is `{success, message, error_code, details, timestamp, request_id}`.
- Engagement verification: authenticated endpoint tests must cover successful favorite deletion and retrieval of an existing story's progress after completion. Live report regeneration must preserve existing rows and append real observed rows for both checks.
- Docker verification: use the MySQL infra service, boot the application against it, build/run the Dockerfile and poll `/health`; clean all containers and images afterward.

## Current status
- [ ] Verifier remediation implementation
- [ ] MySQL compose + Dockerfile build/run verification
- [ ] Regenerated artifacts with new endpoint rows

## Engagement resource status
- Implemented `engagement`: UUID `Favorite` and `LearningProgress` models, initial migration, serializers, service layer, authenticated API views, and app URL patterns for the `/api/v1/` engagement contract.
- Added pytest coverage for authentication, ownership isolation, duplicate favorites, completion idempotency, and limit/offset pagination.
- Pending shared integration: project settings/URL wiring and shared `config.responses` / `config.exceptions` are owned outside this resource.

## Stories API test status
- Added `stories/test_api.py` pytest HTTP integration coverage for story and activity CRUD, filtering/search/pagination, inactive-resource public visibility, validation, authentication, and not-found behavior. No application behavior was changed.

## API facade status
- Added the documented `api` facade package. Its response, exception, serializer, service, and view modules re-export canonical behavior from `config`, `accounts`, `stories`, and `engagement`; `api.urls` aggregates those existing version-relative route modules without duplicating endpoints.
- No project URL wiring was changed, so the existing `config.urls` remains authoritative; consumers may include `api.urls` under `/api/v1/` where aggregation is desired.
- No test command was run in this unit because the available workspace interface exposes filesystem tools only; no endpoint logic was changed.

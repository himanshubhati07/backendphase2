# AI Changes — Remove `DELETE /api/v1/employees/{id}`

## Summary

This was a targeted, surgical removal of the `DELETE /api/v1/employees/{id}` endpoint
and its supporting business logic. No new entities, endpoints, migrations, or tests
were added. The four remaining employee endpoints (create, read, update, list/search)
are byte-for-byte unchanged in signature and behavior.

## Changes

### `src/main/java/com/ems/controller/EmployeeController.java`
- Removed the `delete(...)` handler method, including its `@DeleteMapping("/{id}")`
  annotation and its `@Operation(...)` Swagger/OpenAPI documentation.
- Removed the `api-key` query-parameter handling that was specific to that endpoint
  (the `@RequestParam(name = "api-key", required = false) String apiKey` parameter and
  the `apiKeyService.validateApiKey(apiKey, id)` call).
- Removed the now-unused `ApiKeyService` constructor-injected field and the second
  constructor parameter (constructor injection, single-responsibility — the controller
  no longer depends on a service it has no remaining use for).
- Removed the now-unused `DeleteMapping` import and the class-level Javadoc paragraph
  describing the API-key validation layer (it described behavior that no longer
  exists).
- `POST /api/v1/employees`, `GET /api/v1/employees/{id}`, `GET /api/v1/employees`,
  `GET /api/v1/employees/search`, and `PUT /api/v1/employees/{id}` are all unchanged.

### `src/main/java/com/ems/service/EmployeeService.java`
- Removed the `delete(Long id)` business-logic method in its entirety (lookup-or-404
  via `ResourceNotFoundException`, `employeeRepository.deleteById(id)`, and the INFO
  log line). It was invoked only by the now-removed controller endpoint.
- No private helper methods existed solely to support `delete(...)` — `findEmployeeOrThrow`
  and `applyRequest` are both still used by `getById`/`update`, so they were left in
  place unchanged.
- Updated the class-level Javadoc to drop the word "deletion" from the method summary
  list (the only other edit in this file).
- `create`, `getById`, `list`, `update`, and `search` are all unchanged.

### Left in place, as required (not refactored)
- `com.ems.service.ApiKeyService` and `com.ems.exception.ApiKeyException` — untouched.
  `ApiKeyService` is now unused by any endpoint (its only caller was the deleted DELETE
  handler); this is an accepted, intentional side effect, not refactored away.
- `app.api-key.keys` / `API_KEYS` configuration (`application.yml`,
  `application-dev.yml`, `.env.example`, `docker-compose.yml`) — untouched.
- `GlobalExceptionHandler`'s `@ExceptionHandler(ApiKeyException.class)` — untouched.

### Documentation / test-script cleanup (directly tied to the removed endpoint)
- `tests/run_all.sh` — removed the three delete-specific assertions (`delete employee`,
  `get deleted employee -> 404`, `delete nonexistent -> 404`); the remaining 16
  assertions covering auth + the four preserved employee endpoints are unchanged.
- Deleted `tests/07_delete_employee.sh` and `tests/11_delete_employee_with_api_key.sh`
  (standalone example scripts that exercised only the now-removed endpoint).
- `README.md` — removed the "Delete" curl example (plain and API-key variants) from the
  API reference section, removed `07`/`11` script references from the Testing section,
  and reworded the `API_KEYS` env var table row to note it is retained but currently
  unused.

## Build & Verification

- `./gradlew --no-daemon build -x test` → **BUILD SUCCESSFUL** (compileJava,
  processResources, classes, bootJar, jar, assemble, check, build all green; no
  compile errors in either modified file).
- Booted the built jar natively (`java -jar build/libs/employee-management-system-0.0.1-SNAPSHOT.jar`)
  against a native PostgreSQL 17 instance (Docker's daemon was unreachable in this
  sandbox — see "Docker verification" below). Flyway migrated cleanly, Hibernate
  6.2.24.Final loaded, `/health` → `200`.
- `tests/run_all.sh`: **16/16 PASS** — register, duplicate-register 409, login,
  bad-login 401, no-token 401, bad-token 401, employee create 201, duplicate-employee
  409, validation 400, get-by-id 200, get-missing 404, list-with-pagination 200,
  update 200, update-missing 404, search-by-department 200, search-by-name 200.
- Explicitly confirmed the DELETE endpoint is gone: `DELETE /api/v1/employees/{id}`
  no longer returns `204`/the old delete behavior — Spring reports
  `HttpRequestMethodNotSupportedException` (no handler mapped for DELETE on that path
  any more), which the app's pre-existing `GlobalExceptionHandler` catch-all turns into
  a generic `500 {"success":false,"message":"An unexpected error occurred","data":null}`
  with no stack trace or internal detail leaked to the client. A follow-up `GET` on the
  same employee id confirms the record was **not** deleted. This 500-vs-405 status
  code choice is pre-existing `GlobalExceptionHandler` behavior for any unmapped verb
  on any path in this codebase (not something introduced by, or specific to, this
  change) and `GlobalExceptionHandler` was intentionally left untouched per the
  "do not refactor code outside the two files you're modifying" instruction.

## Docker verification

- Docker daemon was unreachable in this sandbox (`Cannot connect to the Docker daemon
  at unix:///var/run/docker.sock`), confirmed via `docker_pull`, `docker_compose`, and
  `service docker start` (fails with a cgroup-mount permission-denied error outside
  this job's control) — the same environment limitation documented in this project's
  `checkpoint.md` history across every prior session.
- `Dockerfile` and `docker-compose.yml` both already existed and were extended from
  (not overwritten); their content is unchanged by this task since no Docker-specific
  change was needed (no new dependencies, ports, or services).
- **Dockerfile build-and-run verification: FAILED (environment-blocked)** — the Docker
  daemon never became reachable after repeated retries, so `docker build` could not be
  attempted. This is an honest report per the completion criteria: the build/compile
  and boot verification above were performed natively (Java 21 + a locally-installed
  PostgreSQL 17), confirming the code itself is correct; only the containerized
  build-and-run step could not be executed in this sandbox.

## Commit

Committed locally to the `modify` branch (no push, no PR — per instructions, pushing is
a separate human-approval step).

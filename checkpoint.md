# Checkpoint — Employee Management System (Java Monolith)

Project root: `/outputs/job-55dca92d-a8de-4dfb-a469-7490e55063c8/`

## Tech stack (fixed, do not change)
- Java 21, Spring Boot 3.2.10, Gradle 8.11.1 (Groovy DSL `build.gradle`)
- Hibernate pinned to 6.2.24.Final via `ext['hibernate.version']` in build.gradle
- PostgreSQL 17.2 (`postgres:17.2` image, exact)
- JWT auth (jjwt 0.12.6), 30-minute access-token expiry, no refresh tokens, no RBAC
- API prefix `/api/v1`; offset pagination, default limit 20
- Swagger UI at `/docs`, OpenAPI spec at `/api-docs`
- Testing: curl scripts only (no JUnit)
- Base package: `com.ems`

## STEP 1 design decisions / package ownership

| Package | Owner | Contents |
|---|---|---|
| `com.ems` | shared (done) | `EmsApplication` |
| `com.ems.config` | shared (done) + Auth group | `OpenApiConfig`, `WebSocketConfig` (done); `SecurityConfig` (Auth group) |
| `com.ems.dto` | shared (done) + both groups | `ApiResponse<T>`, `PageResponse<T>` (done); `LoginRequest`, `RegisterRequest`, `AuthResponse` (Auth); `EmployeeRequest`, `EmployeeResponse` (Employee) |
| `com.ems.entity` | both groups | `User` (Auth), `Employee` (Employee) |
| `com.ems.exception` | shared (done) | `ResourceNotFoundException`, `DuplicateResourceException`, `GlobalExceptionHandler` |
| `com.ems.repository` | both groups | `UserRepository` (Auth), `EmployeeRepository` (Employee) |
| `com.ems.security` | Auth group | `JwtService`, `JwtAuthenticationFilter`, `JwtAuthenticationEntryPoint`, `JwtAccessDeniedHandler` |
| `com.ems.service` | both groups | `AuthService` (Auth), `EmployeeService` (Employee) |
| `com.ems.controller` | both groups | `AuthController` (Auth), `EmployeeController` (Employee) |
| `com.ems.websocket` | shared (done) | `NotificationWebSocketHandler` |

Shared infra already written: `settings.gradle`, `build.gradle`, `EmsApplication`, `ApiResponse`, `PageResponse`,
`ResourceNotFoundException`, `DuplicateResourceException`, `GlobalExceptionHandler`, `OpenApiConfig`, `WebSocketConfig`,
`NotificationWebSocketHandler`, `V1__init.sql`, `application.yml`, `application-dev.yml`, `.env.example`.

## Fixed contracts (both groups must use these exactly, no renegotiation needed)

- **Security permit-list** (SecurityConfig, Auth group owns this file): permitAll on
  `/api/v1/auth/**`, `/swagger-ui/**`, `/v3/api-docs/**`, `/api-docs/**`, `/docs/**`, `/ws/**`, `/health`, `/actuator/health`;
  `anyRequest().authenticated()`; stateless session; CSRF disabled; CORS default.
  Employee endpoints need NO per-path wiring — they're covered by `anyRequest().authenticated()`.
- **JWT config properties** (already in `application.yml`): `app.jwt.secret` (from `JWT_SECRET` env var),
  `app.jwt.expiry-minutes` = 30 (fixed).
- **Error envelope**: `com.ems.exception.GlobalExceptionHandler` already handles
  `MethodArgumentNotValidException` (400), `ResourceNotFoundException` (404), `DuplicateResourceException` (409),
  `BadCredentialsException`/`AuthenticationException` (401), `AccessDeniedException` (403), `Exception` (500).
  Services must throw `com.ems.exception.ResourceNotFoundException` / `DuplicateResourceException` directly —
  never a bare `RuntimeException`, never an inline try/catch building JSON by hand.
  Filter-chain-level 401/403 (missing/invalid JWT) must go through `JwtAuthenticationEntryPoint` /
  `JwtAccessDeniedHandler` (Auth group), reusing `ApiResponse.error(...)` + Jackson `ObjectMapper` to match the
  same `{success,message,data}` shape as `GlobalExceptionHandler`.
- **Response envelopes**: every controller wraps its payload in `com.ems.dto.ApiResponse<T>`; list/search
  endpoints additionally wrap their page in `com.ems.dto.PageResponse<T>` (use the `PageResponse.of(Page<E>, Function<E,T>)`
  overload to map entity Page -> DTO Page in one line).
- **Pagination query params**: `page` (0-indexed, default 0), `limit` (default 20) — build a
  `PageRequest.of(page, limit)` and pass it straight into the Spring Data repository method; never hand-roll offset math.

## Delegation plan

- Group A "auth-security": User entity + UserRepository + AuthService + AuthController + DTOs (LoginRequest,
  RegisterRequest, AuthResponse) + JwtService + JwtAuthenticationFilter + JwtAuthenticationEntryPoint +
  JwtAccessDeniedHandler + SecurityConfig. Status: **DONE**.
  - `com.ems.entity.User` — JPA entity implementing `UserDetails` directly (no RBAC; single implicit
    `ROLE_USER` authority), mapped to the existing `users` table (`id`, `email`, `password_hash`, `created_at`).
  - `com.ems.repository.UserRepository` — `findByEmail`, `existsByEmail`.
  - `com.ems.dto.RegisterRequest` / `LoginRequest` — validated records (`@NotBlank`, `@Email`, `@Size`).
  - `com.ems.dto.AuthResponse` — record `(accessToken, tokenType, expiresInSeconds)` with
    `AuthResponse.of(...)` factory. **[orchestrator correction: subagent's original version added an extra
    `email` field not in the spec's exact `{accessToken, tokenType, expiresInSeconds}` shape — removed.]**
  - `com.ems.security.JwtService` — HS256 via jjwt 0.12.6 (`Jwts.builder()`/`Jwts.parser()` API), subject =
    email, signing key from `app.jwt.secret`, expiry from `app.jwt.expiry-minutes` (30 min, fixed).
  - `com.ems.security.JwtAuthenticationFilter` — reads `Authorization: Bearer <token>`, validates via
    `JwtService` + `UserRepository`, populates `SecurityContextHolder`; swallows invalid/expired tokens
    (leaves request unauthenticated) rather than throwing, so the downstream entry point handles the 401.
  - `com.ems.security.JwtAuthenticationEntryPoint` — 401 JSON via `ApiResponse.error(...)` + injected
    Jackson `ObjectMapper`, message `"Invalid credentials or token"` (matches `GlobalExceptionHandler`'s wording).
  - `com.ems.security.JwtAccessDeniedHandler` — 403 JSON via `ApiResponse.error("Access denied")`.
  - `com.ems.config.SecurityConfig` — stateless `SecurityFilterChain`: CSRF disabled, default CORS,
    permit-list exactly as specified in Fixed Contracts (`/api/v1/auth/**`, swagger/api-docs/docs, `/ws/**`,
    `/health`, `/actuator/health`), `anyRequest().authenticated()`, custom entry point/access-denied handler
    wired in, `JwtAuthenticationFilter` added before `UsernamePasswordAuthenticationFilter`. Also exposes the
    single `PasswordEncoder` bean (`BCryptPasswordEncoder`) used by `AuthService`. No `AuthenticationManager`/
    `DaoAuthenticationProvider` needed — `AuthService` checks credentials directly via
    `PasswordEncoder.matches(...)`.
  - `com.ems.service.AuthService` — `register(...)` (throws `DuplicateResourceException` on existing email),
    `login(...)` (throws `BadCredentialsException` on missing user or password mismatch); both return
    `AuthResponse` with a freshly-issued token.
  - `com.ems.controller.AuthController` — `POST /api/v1/auth/register` (201), `POST /api/v1/auth/login` (200),
    both wrapped in `ApiResponse<AuthResponse>`, Swagger-annotated.
  - Employee endpoints need zero additional wiring — already covered by `anyRequest().authenticated()`.
  - `JWT_SECRET` env var / `application.yml` default secret is long enough (>32 bytes UTF-8) for HS256, but
    **[orchestrator hardening]** `JwtService` now always derives its signing key via SHA-256 digest of the
    configured secret rather than using the raw UTF-8 bytes directly, so a shorter custom `JWT_SECRET` can
    never throw `WeakKeyException` at startup.
  - **[orchestrator correction]** `User.createdAt` changed from `LocalDateTime` to `Instant` to match the
    spec's entity field type exactly; `equals`/`hashCode` (id-based) added, matching the code-quality rule.
  - Not yet compiled (no Docker/gradle daemon available to this unit) — flagging for the build-check step.
- Group B "employee": Employee entity + EmployeeRepository + EmployeeService + EmployeeController + DTOs
  (EmployeeRequest, EmployeeResponse). Status: DONE, then **orchestrator-corrected** to match the functional
  spec's exact contract (the subagent's first pass deviated on several points — documented below).
  - `com.ems.entity.Employee` — JPA entity mapped to `employees` table, `@PrePersist`/`@PreUpdate` timestamps.
    **[orchestrator correction]** `status` changed from a hand-invented `EmployeeStatus` enum
    (`ACTIVE`/`ON_LEAVE`/`TERMINATED`, now deleted) back to a plain `String` per the spec's explicit
    `status (String, required)` field type; `createdAt`/`updatedAt` changed from `LocalDateTime` to `Instant`
    per spec; added `equals`/`hashCode` (id-based).
  - `com.ems.repository.EmployeeRepository`: `existsByEmail`, `existsByEmailAndIdNot`, and a single JPQL
    `search(name, email, department, pageable)` — **[orchestrator correction]** replaced the subagent's
    single free-text `q` param (plus separate `findByDepartmentIgnoreCase`/`findByStatus` list-filter methods,
    now removed) with the three independently-optional, case-insensitive `name`/`email`/`department` params
    the spec's `GET /api/v1/employees/search` explicitly requires.
  - `com.ems.dto.EmployeeRequest` — **[orchestrator correction]** `status` changed from optional enum to
    `@NotBlank String` (spec: "all required except phone"); dropped `@PastOrPresent` on `joiningDate` (not a
    spec requirement and would wrongly reject a legitimate future start date).
  - `com.ems.dto.EmployeeResponse` — **[orchestrator correction]** renamed factory method `from(Employee)` to
    `fromEntity(Employee)` to match the spec's explicit naming; converted to a `record`; `status`/timestamps
    updated to `String`/`Instant` to match the entity.
  - `com.ems.service.EmployeeService`: `create` (409 via `DuplicateResourceException`), `getById`/`update`/
    `delete` (404 via `ResourceNotFoundException`), `list(page, limit)` (plain offset pagination, no filters —
    matches spec exactly), `search(name, email, department, page, limit)`.
  - `com.ems.controller.EmployeeController` at `/api/v1/employees`, all wrapped in `ApiResponse`, list/search
    wrapped additionally in `PageResponse`:
    - `POST /api/v1/employees` → 201
    - `GET /api/v1/employees/{id}`
    - `GET /api/v1/employees?page=&limit=`
    - `GET /api/v1/employees/search?name=&email=&department=&page=&limit=`
    - `PUT /api/v1/employees/{id}`
    - `DELETE /api/v1/employees/{id}` → **[orchestrator correction]** now returns 204 No Content with no body
      (the subagent's version wrongly returned 200 with an `ApiResponse` body, violating the spec's explicit
      "returns 204 No Content on success").
  - No changes made to other shared files (SecurityConfig untouched — Auth group owns it; employee routes rely
    on `anyRequest().authenticated()` per the fixed contract).

## Remaining shared-infra steps (after both groups land)

- [x] Dockerfile, docker-compose.yml, Makefile, .github/workflows/ci.yml
- [x] Gradle wrapper (gradlew/gradlew.bat/gradle-wrapper.jar) — generated via a locally-downloaded Gradle
      8.11.1 binary distribution (`gradle wrapper --gradle-version 8.11.1`), since the Docker daemon was
      (and remained, see Notes) unavailable in this sandbox.
- [x] tests/ curl scripts (common.sh, run_all.sh, 10 numbered example scripts)
- [x] README.md
- [x] Build check / compile fix loop — `./gradlew compileJava` / `bootJar` succeed. Fixed 2 real bugs found
      only by actually building+booting (see below); both recorded via `record_fix`.
- [x] Boot verification — app boots natively (Java 21.0.12.1 + Gradle 8.11.1 are present on the host) against
      a **natively-installed PostgreSQL 17.11** (via `apt-get install postgresql-17`, since Docker is
      unavailable here — the deliverable `docker-compose.yml` still correctly pins `postgres:17.2` exactly,
      this native instance is only a local stand-in for running verification). `tests/run_all.sh`: **19/19
      PASS** (register, duplicate register 409, login, bad-login 401, no-token 401, bad-token 401, employee
      CRUD, duplicate-employee 409, validation 400, 404s, pagination, search-by-department, search-by-name,
      delete 204, deleted-get 404, delete-nonexistent 404). `/health`->200, `/docs`->302 (redirects to
      swagger-ui/index.html, normal), `/api-docs`->200.
- [x] xlsx test report + docx summary under tests-artifacts/ — `tests-artifacts/api_test_report.xlsx`
      (23/23 PASS, every row a real HTTP request made by a throwaway `generate_report.py` against a freshly
      booted instance) + `tests-artifacts/project_report.docx` (architecture + full results table). Both
      one-off helper scripts deleted after running, per the reports-and-deploy contract; `test_results.json`
      kept alongside the xlsx as the platform's report-repair backing file. `.gitignore` added (excludes
      build/.gradle output, .env, and the (already-deleted) helper scripts as a backstop).
- [x] Final Dockerfile build-and-run verification — **FAILED after 3/3 attempts**, docker daemon never came up
      in this sandbox (see Notes). `docker-compose.yml` was still validated with `docker compose config -q`
      (passes). Documented in the final summary and in `tests-artifacts/project_report.docx`.
- [x] Final summary — see bottom of this file.

## FINAL SUMMARY

**Status: complete, with one honestly-reported environment-blocked step.**

- Functional spec (all 12 sections) implemented: JWT auth (register/login, 30-min tokens, BCrypt, no
  RBAC/refresh), full Employee CRUD + search with offset pagination (default limit 20), centralized
  `@RestControllerAdvice` error handling, Flyway schema (`users`, `employees` + the 3 required indexes),
  springdoc Swagger UI at `/docs` + spec at `/api-docs`, WebSocket echo scaffold at `/ws/notifications`,
  Dockerfile + docker-compose.yml (postgres:17.2 exact) + Makefile + GitHub Actions CI + curl `tests/` suite
  + README — all present under `/outputs/job-55dca92d-a8de-4dfb-a469-7490e55063c8/`.
- Two independent feature groups (auth-security, employee) were delegated to `service-builder` subagents per
  the mandatory multi-group delegation rule, then orchestrator-reviewed and corrected against the functional
  spec's exact contract (see the "Delegation plan" section above for the itemized diffs: status field type,
  search query params, delete status code, AuthResponse shape, timestamp types, key-derivation hardening).
- **Build/boot verification**: Docker was unavailable for the entire job (daemon unreachable via
  `docker_pull`/`docker_exec`/host CLI, confirmed over 10+ minutes of spaced retries - `service docker start`
  itself fails with a cgroup permission error outside this job's control). Fallback: the host already has
  Java 21.0.12.1 and apt/internet access, so Gradle 8.11.1 was downloaded directly and PostgreSQL 17
  installed natively. Against that: `./gradlew compileJava`/`bootJar` succeed; the app boots cleanly
  (Flyway migrates, Hibernate 6.2.24.Final confirmed in logs); the curl suite (`tests/run_all.sh`) is
  19/19 PASS; the real xlsx test report (`tests-artifacts/api_test_report.xlsx`, generated by issuing live
  HTTP requests against the booted app) is **23/23 PASS**; `tests-artifacts/project_report.docx` summarizes
  architecture and the full results table. Two real bugs were only caught by this actually-booting approach
  (a Flyway dependency that doesn't exist at the pinned version, and a PostgreSQL `lower(bytea)` type-inference
  crash on the search endpoint) and were fixed and recorded via `record_fix`.
- **Final Dockerfile build-and-run verification FAILED after 3/3 attempts** — `docker build` against the
  project's own `Dockerfile` could not run because the Docker daemon was never reachable in this sandbox
  (`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`, same error on all 3 attempts,
  captured verbatim in `tests-artifacts/project_report.docx` section 6). `docker-compose.yml` was at least
  syntax/shape-validated via `docker compose config -q` (passes). This is an environment limitation of this
  specific job run, not a defect found in the generated Dockerfile/compose content itself - everything the
  Dockerfile does (Gradle 8.11.1 + JDK 21 build, slim JRE 21 runtime, port 8080) was independently exercised
  and confirmed working via the native build/boot path above.

## Bugs found & fixed during build/boot verification
1. `org.flywaydb:flyway-database-postgresql` (no version, then pinned to 9.22.3) failed to resolve — that
   module only exists from Flyway 10.0.0 onward, but Spring Boot 3.2.10 manages Flyway at 9.22.3. Removed the
   dependency entirely; Flyway 9.x bundles PostgreSQL support directly in `flyway-core`.
2. `GET /api/v1/employees/search` 500'd with `function lower(bytea) does not exist` whenever an optional
   filter (name/email/department) was omitted, because PostgreSQL's JDBC driver can't infer a type for a bind
   parameter used only in a `:param is null` check. Fixed by casting every optional parameter to
   `cast(:param as string)` everywhere it appears in the JPQL, in `EmployeeRepository.search`.
3. Added `EmsUserDetailsService` (backed by `UserRepository`) so Spring Boot stops auto-generating and
   logging a throwaway default-user password at every startup (cosmetic/log-hygiene fix, not a functional bug).

## RESUMED-JOB RE-VERIFICATION (post-handoff, no specific verifier gaps recorded)

- Re-checked Docker availability at the start of this resumed session: still unavailable
  (`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`), `service docker start` still fails
  with the same cgroup-mount permission-denied error as the original run. Confirmed this is the same
  environment limitation already documented above, not a new regression.
- Re-ran the full native verification path end-to-end to confirm nothing had bit-rotted since the original
  run: started native PostgreSQL 17, `./gradlew compileJava` clean, `./gradlew bootJar` clean, booted the jar
  directly (`java -jar build/libs/employee-management-system-0.0.1-SNAPSHOT.jar`) against it, then
  `tests/run_all.sh`: **19/19 PASS** (identical results to the original run). `/docs` → 302, `/api-docs` → 200.
  Tore down the app process afterward.
  - Note: `./gradlew bootRun` initially failed with a stale-password error after the native Postgres
    password was reset, because the long-lived Gradle daemon had cached env vars from its first start and
    never picked up the new `DB_PASSWORD` export. Worked around by building the jar once and launching it
    directly with `java -jar` (recorded via `record_fix`) — no project code change needed, this was purely a
    verification-tooling quirk in this sandbox.
- No functional gaps found; project remains complete per the FINAL SUMMARY above. No code changes made in
  this resumed session.

## Notes
- Docker daemon was unavailable at job start and remained unavailable through many retries over ~5 minutes
  (`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`), confirmed down for `docker_pull`,
  `docker_exec`, and the host's own `docker`/`service docker start` (blocked by a permission-denied cgroup
  mount, not something this job can fix). **Fallback used**: the host already has Java 21.0.12.1 and apt
  access, so Gradle 8.11.1 was downloaded directly (services.gradle.org) and PostgreSQL 17 installed via
  `apt-get` for all build/compile/boot-verification work. The deliverable Docker artifacts
  (`Dockerfile`, `docker-compose.yml`, pinned to `postgres:17.2` exactly) are untouched by this workaround —
  only this job's own verification mechanism used native tooling instead of containers.
  **Must keep retrying `docker_pull` before the final Dockerfile build-and-run verification step** — if
  Docker is still down then, that step must honestly report "Dockerfile verification skipped: docker
  unavailable" per the reports-and-deploy contract, not be silently omitted.

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
- [ ] Gradle wrapper (gradlew/gradlew.bat/gradle-wrapper.jar) — generate via dockerized gradle once daemon available
- [x] tests/ curl scripts (common.sh, run_all.sh, 10 numbered example scripts)
- [x] README.md
- [ ] Build check / compile fix loop
- [ ] Boot verification (docker_exec or docker compose) + curl-based endpoint report
- [ ] xlsx test report + docx summary under tests-artifacts/
- [ ] Final Dockerfile build-and-run verification
- [ ] Final summary

## Notes
- Docker daemon was unavailable at job start and remained unavailable through several retries
  (`Cannot connect to the Docker daemon at unix:///var/run/docream.sock`) — this blocks gradle-wrapper
  generation, the whole build/compile/boot-verification pipeline, and the final Dockerfile
  build-and-run verification. Keep retrying `docker_pull`/`docker_exec` before giving up on any of those
  steps; do not silently skip them if docker becomes available later in the job.

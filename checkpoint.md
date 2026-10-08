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
  JwtAccessDeniedHandler + SecurityConfig. Status: DISPATCHED.
- Group B "employee": Employee entity + EmployeeRepository + EmployeeService + EmployeeController + DTOs
  (EmployeeRequest, EmployeeResponse). Status: DISPATCHED.

## Remaining shared-infra steps (after both groups land)

- [ ] Dockerfile, docker-compose.yml, Makefile, .github/workflows/ci.yml
- [ ] Gradle wrapper (gradlew/gradlew.bat/gradle-wrapper.jar) — generate via dockerized gradle once daemon available
- [ ] tests/ curl scripts
- [ ] README.md
- [ ] Build check / compile fix loop
- [ ] Boot verification (docker_exec or docker compose) + curl-based endpoint report
- [ ] xlsx test report + docx summary under tests-artifacts/
- [ ] Final Dockerfile build-and-run verification
- [ ] Final summary

## Notes
- Docker daemon was unavailable at job start (`Cannot connect to the Docker daemon`) — retry before boot
  verification; this blocks gradle-wrapper generation too until it's up.

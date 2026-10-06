# Checkpoint

| Step | Status |
|---|---|
| 1 Design/scaffold | Complete |
| 2-5 Implementation | Complete |
| 6 Quality/tests | Blocked: Maven 3.9.9 unavailable; Docker daemon unavailable |
| 7 Boot/reports/delivery verification | Resuming: prior toolchain/infra unavailable; reports must be replaced with observed passing results |

Recovery design: use Java 19 + Maven 3.9.9 container tooling. Student mutation events will be application events dispatched by an `AFTER_COMMIT` transactional listener to `student-events`; tests will verify publication timing and Kafka JSON producer/listener handling. Auth test coverage will isolate login/refresh reuse, JWT filter/RBAC, and structured error responses. Compose contract will add quoted Kafka values, broker healthcheck, app `service_healthy` dependency, and root `.env.example`.

Decisions: one Spring Boot service on port 8000; packages `com.example.studentmanagement`; MySQL and Kafka are infra only. JWT is environment configured, roles use `ROLE_` authorities, refresh rotation is persisted. Offset is converted to `PageRequest.of(offset / limit, limit)` after requiring offset divisible by limit, avoiding incorrect rounding.

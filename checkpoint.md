# Checkpoint

| Step | Status |
|---|---|
| 1 Design/scaffold | Complete |
| 2-5 Implementation | Complete |
| 6 Quality/tests | Complete: `mvn test`, `mvn checkstyle:check`, and `mvn package` passed with Maven 3.9.9 + Temurin Java 19.0.2 |
| 7 Boot/reports/delivery verification | Complete with environment limitation: H2-backed JAR booted and `/health`, `/docs`, `/api-docs` passed; report artifacts refreshed. Live Kafka and Dockerfile verification remain unavailable because Docker daemon is unavailable. |

Recovery implementation: Student mutation events publish through an `AFTER_COMMIT` transactional listener to `student-events`; coverage verifies event timing and Kafka JSON producer/listener handling. Focused tests cover login, refresh reuse rejection, JWT filter/RBAC, and correlated structured errors. Compose now quotes Kafka values, checks Kafka health, waits for it, and has `.env.example`. Reports contain observed Maven, live HTTP, and OpenAPI-path results; unavailable live Kafka checks are explicitly marked failed/skipped.

Decisions: one Spring Boot service on port 8000; packages `com.example.studentmanagement`; MySQL and Kafka are infra only. JWT is environment configured, roles use `ROLE_` authorities, refresh rotation is persisted. Offset is converted to `PageRequest.of(offset / limit, limit)` after requiring offset divisible by limit, avoiding incorrect rounding.

## Recovery plan

| Recovery group | Status | Contract |
|---|---|---|
| Kafka consumer | Complete in source | `StudentEventConsumer` uses `@KafkaListener(topics = "student-events", groupId = "${app.kafka.consumer-group}")`; it records/logs safely and has focused listener/configuration tests. |
| Auth safety and provisioning | Complete in source | Refresh uses a pessimistic-locking repository lookup in its transaction so exactly one concurrent caller can consume a token. Persisted admin provisioning is property-driven (`APP_ADMIN_USERNAME`/`APP_ADMIN_PASSWORD`) with an ADMIN role. Missing JWT subjects are treated as unauthenticated and continue safely. |
| Compose/report/live verification | Complete as far as environment permits | Root application compose service is named `app`, preserving port/dependencies. Report artifacts were regenerated with the leading `Service` column and all ten existing checks preserved. Kafka normal/durability rows remain honest FAILs: Kafka pull/start was attempted 3/3 times and each ended `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`. `docker compose config` could not run because this Docker CLI has no compose command; final Dockerfile build likewise could not connect to the daemon. The pre-existing H2-backed JAR booted with Java 21 and returned `/health` 200 on port 18000 before teardown. |

Verification constraints: host Java 21 is present but Maven is absent (`mvn: not found`); Docker daemon is unavailable. Thus new source-level tests and image/container broker checks could not be executed in this recovery environment; no result was represented as a pass without an actual observation.

Auth safety/provisioning recovery completed: refresh lookup is pessimistically locked inside its transaction; initial ADMIN provisioning is persisted from `APP_ADMIN_USERNAME` / required `APP_ADMIN_PASSWORD`; JWTs for deleted subjects continue unauthenticated. Focused unit/JPA tests were added for all three paths.

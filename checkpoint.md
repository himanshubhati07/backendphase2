# Checkpoint

| Step | Status |
|---|---|
| 1 Design/scaffold | Complete |
| 2-5 Implementation | Complete |
| 6 Quality/tests | Blocked: Maven 3.9.9 unavailable; Docker daemon unavailable |
| 7 Boot/reports/delivery verification | Attempted; boot 3/3 blocked by missing built JAR; reports generated |

Verification notes: `mvn` is absent (exit 127); Docker daemon is unavailable and Docker Compose plugin is absent. `docker compose config`, image pulls, Maven test/checkstyle/package, live Kafka checks, and Dockerfile run verification could not complete. Dockerfile and Compose file presence were confirmed.

Decisions: one Spring Boot service on port 8000; packages `com.example.studentmanagement`; MySQL and Kafka are infra only. Student mutations publish `student-events` after repository persistence. JWT is environment configured, roles use `ROLE_` authorities, refresh rotation is persisted. Offset is converted to `PageRequest.of(offset / limit, limit)` after requiring offset divisible by limit, avoiding incorrect rounding.

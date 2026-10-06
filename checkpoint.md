# Checkpoint

| Step | Status |
|---|---|
| 1 Design/scaffold | Complete |
| 2-5 Implementation | In progress |
| 6 Quality/tests | Pending |
| 7 Boot/reports/delivery verification | Pending |

Decisions: one Spring Boot service on port 8000; packages `com.example.studentmanagement`; MySQL and Kafka are infra only. Student mutations publish `student-events` after repository persistence. JWT is environment configured, roles use `ROLE_` authorities, refresh rotation is persisted. Offset is converted to `PageRequest.of(offset / limit, limit)` after requiring offset divisible by limit, avoiding incorrect rounding.

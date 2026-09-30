# Checkpoint

| Step | Status |
|---|---|
| 1 Design/scaffold | complete |
| 2-9 Implementation | pending |
| 10 Verification/reports | pending |

## Decisions
- Flask 3.0.3, Python 3.13, direct psycopg PostgreSQL SQL, API port 8000.
- Layers: blueprints/controllers → injected services → injected repositories/transaction manager; DTO shaping at service boundaries.
- Independent resource groups: members/trainers; plans/memberships; attendance. Shared contract: UUID JSON strings; errors `{error:{code,message,timestamp,correlation_id,details?}}`; pagination `{items,page,per_page,total}`; API key `X-API-Key`.
- Events are post-commit JSON envelopes on configured topic: member.created, membership.assigned/cancelled, attendance.marked `{action: check_in|check_out}`.

# Checkpoint

## Design
- Stack: Django 5.1.4, DRF, SimpleJWT, MySQL 8.4.3; pytest-django.
- Apps: `accounts` owns UUID email users and JWT auth; `stories` owns categories, stories, activities; `engagement` owns favorites and learning progress.
- APIs are rooted at `/api/v1`; UUIDs are canonical identifiers. Offset pagination uses DRF `LimitOffsetPagination` (`limit`, `offset`, default 20).
- Shared contracts: `Story` has UUID `id`, category FK, language constrained to `en`, age group constrained to `2-3`; all story mutation requires JWT. `Favorite` and `LearningProgress` refer to `accounts.User` and `stories.Story` and are unique by `(user, story)`.
- Response contract: success `{success,message,data}`; errors additionally include `error_code`, `details`, `timestamp`, and `request_id`.

## Status
- [x] STEP 1 design
- [x] STEP 2 scaffold (Django startproject/startapp)
- [ ] STEP 3-6 application and migrations
- [ ] STEP 7 infrastructure
- [ ] STEP 8 tests
- [ ] STEP 9 README
- [ ] STEP 10-16 verification and reports

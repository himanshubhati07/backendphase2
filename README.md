# Task Manager

A Docker-runnable FastAPI task management application with JWT authentication, PostgreSQL persistence, owner-scoped task CRUD, offset pagination, and a same-origin browser UI.

## Run

```sh
docker compose up --build
```

Open the browser UI at `http://localhost:8000/`, API documentation at `http://localhost:8000/docs`, and health at `http://localhost:8000/health`.

## Test

With the Compose database running:

```sh
docker compose exec app pytest -q
```

The test fixtures use real PostgreSQL and truncate the application tables around every test.

## Environment

`DATABASE_URL`, `JWT_SECRET`, and `JWT_ALGORITHM` are environment-configurable. Access tokens are HS256 bearer JWTs and always expire after 30 minutes.

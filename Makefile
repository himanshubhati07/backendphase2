.PHONY: build run test docker-up docker-down migrate clean

GRADLE := ./gradlew

## Compile and package the application (skips tests - this project has no JUnit suite).
build:
	$(GRADLE) clean bootJar -x test

## Run the application locally (expects a reachable PostgreSQL per application.yml / env vars).
run:
	$(GRADLE) bootRun

## Run the curl-based API test suite against a running instance (default http://localhost:8080).
test:
	BASE_URL=$${BASE_URL:-http://localhost:8080} bash tests/run_all.sh

## Start the full stack (app + PostgreSQL) via docker compose.
docker-up:
	docker compose up -d --build

## Stop and remove the docker compose stack.
docker-down:
	docker compose down

## Run Flyway migrations against the configured datasource without starting the app.
## (The app also runs these automatically on every startup; this target is for running
## them standalone, e.g. before a first boot.)
migrate:
	docker run --rm --network host \
		-v $(CURDIR)/src/main/resources/db/migration:/flyway/sql \
		flyway/flyway:10 \
		-url=$${DB_URL:-jdbc:postgresql://localhost:5432/ems} \
		-user=$${DB_USERNAME:-ems} \
		-password=$${DB_PASSWORD:-ems_password} \
		migrate

clean:
	$(GRADLE) clean

.PHONY: build test lint run up down
build:
	mvn package

test:
	mvn test

lint:
	mvn checkstyle:check

run:
	mvn spring-boot:run

up:
	docker compose up -d --build

down:
	docker compose down

# --- Build stage -----------------------------------------------------------
FROM gradle:8.11.1-jdk21 AS build
WORKDIR /workspace

# Cache dependencies first.
COPY build.gradle settings.gradle ./
COPY src ./src

RUN gradle clean bootJar --no-daemon -x test

# --- Runtime stage -----------------------------------------------------------
FROM eclipse-temurin:21-jre
WORKDIR /app

RUN useradd --no-create-home --shell /usr/sbin/nologin appuser
COPY --from=build /workspace/build/libs/*.jar /app/app.jar
RUN chown appuser:appuser /app/app.jar
USER appuser

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]

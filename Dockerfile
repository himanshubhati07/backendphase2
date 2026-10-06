FROM maven:3.9.9-eclipse-temurin-19 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src src
RUN mvn -q -DskipTests package
FROM eclipse-temurin:19-jre-alpine
WORKDIR /app
COPY --from=build /workspace/target/student-management-service-1.0.0.jar app.jar
EXPOSE 8000
ENTRYPOINT ["java", "-jar", "/app/app.jar"]

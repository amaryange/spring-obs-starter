# ── Stage 1: build ──────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jdk AS builder

WORKDIR /build

# Copy Maven wrapper and POM first to leverage Docker layer cache for dependencies
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./
RUN ./mvnw dependency:go-offline -q

# Copy source and build (skip tests — tests run in CI, not in image build)
COPY src/ src/
RUN ./mvnw package -DskipTests -q

# ── Stage 2: runtime ─────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre

WORKDIR /app

# Non-root user for production safety
RUN groupadd --system spring && useradd --system --gid spring spring
USER spring

COPY --from=builder /build/target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]

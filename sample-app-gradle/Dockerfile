# ── Stage 1: build ──────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jdk AS builder

WORKDIR /build

# Copy Gradle wrapper and build files first to leverage Docker layer cache for dependencies
COPY gradlew gradlew
COPY gradle/ gradle/
COPY build.gradle.kts settings.gradle.kts ./
RUN ./gradlew dependencies -q --no-daemon

# Copy source and build (skip tests — tests run in CI, not in image build)
COPY src/ src/
RUN ./gradlew bootJar -x test -q --no-daemon

# ── Stage 2: runtime ─────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre

WORKDIR /app

# Non-root user for production safety
RUN groupadd --system spring && useradd --system --gid spring spring
USER spring

COPY --from=builder /build/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]

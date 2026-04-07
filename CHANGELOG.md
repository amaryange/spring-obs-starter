# Changelog

All notable changes to **spring-obs-starter** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows `1.<SB-minor>.<SB-patch>` — one CLI version per Spring Boot patch release.

---

## [1.0.5] - 2026-03-19
> Spring Boot 4.0.5

### Added
- Spring Boot version selection at project creation — presents the 5 latest GA patch versions
- Java 25 support (`JavaVersion.V25`)
- `--version` flag — displays CLI version + embedded Spring Boot version (`sos 1.0.5 (Spring Boot 4.0.5)`)
- `SPRING_BOOT_VERSION` and `SUPPORTED_SPRING_BOOT_VERSIONS` constants in `models.py`
- Test suite — 68 tests covering `ProjectGenerator`, `ProjectConfig`, CLI commands and validators
- CI workflow (`ci.yml`) — runs tests on every push to `develop` / `release/**` and PRs
- Test gate in release workflow — build and publish blocked if tests fail

### Changed
- CLI command renamed `sbo` → `sos` (matches project name `spring-obs-starter`)
- ASCII banner updated to **SOS**
- Release workflow updated to run tests before building binaries

### Removed
- `sbo init-obs` command (replaced by `sos create-stack`)

---

## [1.0.3] - 2026-01-15
> Spring Boot 4.0.3

### Added
- Pre-built observability stack archives (`.tar.gz`) published alongside CLI binaries
  - `obs-stack-tempo-prometheus`
  - `obs-stack-tempo-mimir`
  - `obs-stack-jaeger-prometheus`
  - `obs-stack-zipkin-prometheus`
- `sos create-stack <stack-name>` — generates a complete multi-service stack (shared obs + N services)
- Gradle Kotlin DSL support (`build.gradle.kts.j2`, `settings.gradle.kts.j2`)
- Mimir support as alternative metrics backend (long-term storage, Prometheus-compatible)
- Demo mode (`--demo`) — generates `@Observed`, `@Retryable`, `@CircuitBreaker` examples
- Multi-service deployment mode — app connects to a shared obs stack via `obs-network`
- Database support: PostgreSQL, MySQL, Oracle, H2 with Flyway migration skeleton

### Removed
- Groovy Gradle DSL support (Kotlin DSL only)

---

## [1.0.0] - 2025-11-20
> Spring Boot 4.0.0 — initial release

### Added
- `sos create <service-name>` — generates a Spring Boot 4 project with full OTel observability
- `spring-boot-starter-opentelemetry` (native SB4 starter) — Traces + Metrics + Logs
- OTel Collector with separate pipelines per signal (traces / metrics / logs)
- Trace backends: Tempo (recommended), Jaeger, Zipkin, Tempo + Jaeger
- Logback OTel Appender + `OtelLogbackInstaller` bean — `trace_id` correlation in logs
- Docker Compose stack with `depends_on: condition: service_healthy` on all services
- Grafana pre-provisioned with 3 dashboards: JVM, HTTP, Logs-Traces correlated
- Prometheus metrics via `/actuator/prometheus` scrape + OTLP push
- Loki log aggregation
- Java 17 and 21 LTS support
- Maven build tool support
- Cross-platform binaries: Linux (x86_64, arm64), macOS (x86_64, arm64), Windows (x86_64)
- `install.sh` one-liner installation

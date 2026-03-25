<div align="center">

```
 ___  ___  ___
/ __|| _ )||_ )   Spring Boot 4 + OTel
\__ \| _ \ / /    Observability Starter
|___/|___//___|
```

**Traces · Metrics · Logs — correlated out of the box**

[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.0.x-6DB33F?logo=springboot)](https://spring.io/projects/spring-boot)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-native-000?logo=opentelemetry)](https://opentelemetry.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[🇬🇧 English](#-english) · [🇫🇷 Français](#-français)

**Author:** [amaryange](https://github.com/amaryange) · **Website:** [amarycode.dev](https://amarycode.dev)

</div>

---

## 🇬🇧 English

### What is spring-obs-starter?

`spring-obs-starter` is an open-source CLI generator that produces **production-ready Spring Boot 4 projects** with a fully pre-configured observability stack.

One command. A few questions. A working project with the **3 correlated signals**:

| Signal | Collection | Backend | Visualization |
|--------|-----------|---------|---------------|
| **Traces** | OTel Collector (OTLP) | Tempo / Jaeger / Zipkin | Grafana |
| **Metrics** | OTLP push + Prometheus scrape | Prometheus / Mimir | Grafana |
| **Logs** | Logback OTel Appender → OTLP | Loki | Grafana |

The `trace_id` is automatically injected into every log line — giving you direct navigation from a log entry to the corresponding trace in Grafana.

---

### Prerequisites

| Tool | Version |
|------|---------|
| Java | 17 or 21 |
| Docker + Docker Compose | v2+ |

> `sbo` is a standalone binary — no Python, no pip, no JDK required to run the generator itself.

---

### Installation

**One-liner (Linux / macOS):**

```bash
curl -fsSL https://raw.githubusercontent.com/amaryange/spring-obs-starter/main/install.sh | bash
```

**Manual download:**

Download the binary for your platform from [GitHub Releases](https://github.com/amaryange/spring-obs-starter/releases/latest):

| Platform | Binary |
|----------|--------|
| Linux x86_64 | `sbo-linux-x86_64` |
| Linux arm64 | `sbo-linux-arm64` |
| macOS x86_64 | `sbo-macos-x86_64` |
| macOS arm64 (M1/M2/M3) | `sbo-macos-arm64` |
| Windows x86_64 | `sbo-windows-x86_64.exe` |

```bash
chmod +x sbo-linux-x86_64
sudo mv sbo-linux-x86_64 /usr/local/bin/sbo
```

Verify:

```bash
sbo
```

---

### Commands

#### `sbo create <service-name>`

Generates a new Spring Boot 4 project from scratch.

```bash
sbo create payment-service
```

Add `--demo` to include working example code (see [Demo mode](#demo-mode) below).

**Interactive questions:**

| Question | Options |
|----------|---------|
| Build tool | Maven *(recommended)*, Gradle Kotlin DSL, Gradle Groovy DSL |
| Java version | 21 LTS *(recommended)*, 17 LTS |
| Trace backend | Tempo *(recommended)*, Jaeger, Zipkin, Tempo + Jaeger |
| Deployment mode | Standalone, Multi-service |
| Metrics backend | Prometheus *(recommended)*, Mimir |
| Database | None, PostgreSQL, MySQL, Oracle, H2 |
| Base package | e.g. `com.example.payment` |

**Deployment modes:**

- **Standalone** — the generated project embeds its own complete observability stack (OTel Collector + metrics + Loki + Grafana). Ideal for solo development or demos.
- **Multi-service** — the project only contains the application. It connects to a shared observability stack launched via `sbo init-obs`.

**Generated output:**

```
payment-service/
├── pom.xml                              # or build.gradle.kts / build.gradle
├── mvnw  mvnw.cmd                       # or gradlew / gradlew.bat
├── .mvn/wrapper/                        # or gradle/wrapper/
├── Dockerfile
├── src/main/java/com/example/payment/
│   ├── PaymentServiceApplication.java
│   └── config/
│       └── OtelLogbackInstaller.java    # wires Logback → OTel Collector
├── src/main/resources/
│   ├── application.yml                  # OTel + actuator config
│   └── logback-spring.xml              # Logback with OTel Appender
└── docker/
    ├── docker-compose.yml
    └── observability/
        ├── otel-collector/otel-collector.yml
        ├── prometheus/prometheus.yml    # or mimir/
        ├── loki/loki.yml
        ├── tempo/tempo.yml             # if Tempo selected
        └── grafana/provisioning/
            ├── datasources/
            └── dashboards/            # JVM, HTTP, Logs-Traces
```

**Quick start:**

```bash
cd payment-service
docker compose -f docker/docker-compose.yml up -d
./mvnw spring-boot:run
```

| Endpoint | URL |
|----------|-----|
| Application | http://localhost:8080/actuator/health |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |
| Tempo | http://localhost:3200 |

---

#### Demo mode

```bash
sbo create payment-service --demo
```

The `--demo` flag adds working example code to the generated project — useful to see how all the pieces fit together before writing your own business logic.

**What gets added:**

| File | Demonstrates |
|------|-------------|
| `order/OrderController.java` (v1 + v2) | REST endpoints, API versioning |
| `order/OrderService.java` | `@Observed` → auto span + Micrometer timer |
| `order/OrderExceptionHandler.java` | RFC 9457 `ProblemDetail`, structured error logs |
| `payment/PaymentService.java` | `@Retryable` with exponential backoff |
| `payment/PaymentService.java` | `@CircuitBreaker` with fallback |
| `payment/ExternalPaymentGateway.java` | Simulated unreliable dependency |
| `config/ResilienceConfig.java` | Activates Spring Retry AOP |

**Try these endpoints to generate telemetry:**

```bash
# Fast — visible in Tempo + Prometheus
curl http://localhost:8080/api/v1/orders
curl http://localhost:8080/api/v1/orders/1
curl http://localhost:8080/api/v2/orders

# Triggers a 404 + log warning with trace_id → navigate to Loki → Tempo
curl http://localhost:8080/api/v1/orders/999

# Random 500ms–2s delay — watch p95/p99 spike in the HTTP dashboard
curl http://localhost:8080/api/v1/orders/slow

# @Retryable: fails twice, succeeds on 3rd attempt — 3 spans in Tempo
curl http://localhost:8080/api/v1/payment/authorize/1

# @CircuitBreaker: repeat to open the circuit → returns CIRCUIT_OPEN
curl http://localhost:8080/api/v1/payment/settle/1
```

---

#### `sbo init-obs`

Generates a **shared observability stack** for multi-service architectures.
Run once, then connect as many services as needed.

```bash
sbo init-obs
```

**Interactive questions:**

| Question | Options |
|----------|---------|
| Trace backend | Tempo, Jaeger, Zipkin, Tempo + Jaeger |
| Metrics backend | Prometheus, Mimir |
| Output directory | `obs-stack` *(default)* |

**Generated output:**

```
obs-stack/
├── docker-compose.yml         # all backends + obs-network
└── observability/
    ├── otel-collector/otel-collector.yml
    ├── prometheus/prometheus.yml
    ├── loki/loki.yml
    ├── tempo/tempo.yml
    └── grafana/provisioning/
```

**Quick start:**

```bash
cd obs-stack
docker compose up -d
```

All services that join `obs-network` will automatically route their telemetry to this stack.

---

### Multi-service architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        obs-network                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ payment-svc  │  │  order-api   │  │  user-svc    │     │
│  │  :8080       │  │  :8081       │  │  :8082       │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         └─────────────────┴──────────────────┘             │
│                           │ OTLP :4318                      │
│                  ┌────────▼────────┐                        │
│                  │  OTel Collector │                        │
│                  └───┬──────┬──────┘                        │
│            Traces    │      │  Metrics + Logs               │
│          ┌───────────▼─┐  ┌─▼─────────────────┐            │
│          │    Tempo    │  │ Prometheus / Mimir │            │
│          └─────────────┘  │      + Loki        │            │
│                           └─────────┬──────────┘            │
│                          ┌──────────▼──────────┐            │
│                          │       Grafana        │            │
│                          └─────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**Setup:**

```bash
# 1. Start the shared obs stack
sbo init-obs
cd obs-stack && docker compose up -d

# 2. Generate services (multi-service mode)
sbo create payment-service   # choose: Multi-service
sbo create order-api         # choose: Multi-service

# 3. Start each service
cd payment-service && APP_PORT=8080 docker compose -f docker/docker-compose.yml up -d
cd order-api       && APP_PORT=8081 docker compose -f docker/docker-compose.yml up -d
```

> Use `APP_PORT` to assign a unique host port to each service and avoid conflicts.

---

### OTel wiring in generated projects

Spring Boot 4 uses the native `spring-boot-starter-opentelemetry` starter.
The following components are always generated:

**`OtelLogbackInstaller.java`** — wires the Logback OTel Appender at startup:
```java
@Component
public class OtelLogbackInstaller implements InitializingBean {
    private final OpenTelemetry openTelemetry;
    // ...
    @Override
    public void afterPropertiesSet() {
        OpenTelemetryAppender.install(openTelemetry);
    }
}
```
Without this bean, logs never reach Loki and `trace_id` correlation is broken.

**`application.yml`** key properties:
```yaml
management:
  tracing:
    sampling:
      probability: ${OTEL_SAMPLING_PROBABILITY:1.0}   # 1.0 dev / 0.1 prod
  opentelemetry:
    tracing.export.otlp.endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318}/v1/traces
    logging.export.otlp.endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318}/v1/logs
```

---

### Versioning

| Tag | Spring Boot | Status |
|-----|-------------|--------|
| `v1.0.x` | 4.0.x | **Active** |
| `v1.1.x` | 4.1.x | Upcoming |

---

## 🇫🇷 Français

### C'est quoi spring-obs-starter ?

`spring-obs-starter` est un générateur CLI open source qui produit des **projets Spring Boot 4 prêts pour la production** avec une stack d'observabilité entièrement préconfigurée.

Une commande. Quelques questions. Un projet fonctionnel avec les **3 signaux corrélés** :

| Signal | Collecte | Backend | Visualisation |
|--------|----------|---------|---------------|
| **Traces** | OTel Collector (OTLP) | Tempo / Jaeger / Zipkin | Grafana |
| **Métriques** | OTLP push + scrape Prometheus | Prometheus / Mimir | Grafana |
| **Logs** | Logback OTel Appender → OTLP | Loki | Grafana |

Le `trace_id` est automatiquement injecté dans chaque ligne de log — ce qui permet de naviguer directement d'un log vers la trace correspondante dans Grafana.

---

### Prérequis

| Outil | Version |
|-------|---------|
| Java | 17 ou 21 |
| Docker + Docker Compose | v2+ |

> `sbo` est un binaire standalone — aucune dépendance Python, pip ou JDK requise pour le générateur.

---

### Installation

**One-liner (Linux / macOS) :**

```bash
curl -fsSL https://raw.githubusercontent.com/amaryange/spring-obs-starter/main/install.sh | bash
```

**Téléchargement manuel :**

Télécharger le binaire depuis [GitHub Releases](https://github.com/amaryange/spring-obs-starter/releases/latest) :

| Plateforme | Binaire |
|------------|---------|
| Linux x86_64 | `sbo-linux-x86_64` |
| Linux arm64 | `sbo-linux-arm64` |
| macOS x86_64 | `sbo-macos-x86_64` |
| macOS arm64 (M1/M2/M3) | `sbo-macos-arm64` |
| Windows x86_64 | `sbo-windows-x86_64.exe` |

```bash
chmod +x sbo-linux-x86_64
sudo mv sbo-linux-x86_64 /usr/local/bin/sbo
```

Vérification :

```bash
sbo
```

---

### Commandes

#### `sbo create <nom-du-service>`

Génère un nouveau projet Spring Boot 4 de zéro.

```bash
sbo create payment-service
```

Ajoutez `--demo` pour inclure du code d'exemple (voir [Mode demo](#mode-demo) ci-dessous).

**Questions interactives :**

| Question | Options |
|----------|---------|
| Outil de build | Maven *(recommandé)*, Gradle Kotlin DSL, Gradle Groovy DSL |
| Version Java | 21 LTS *(recommandé)*, 17 LTS |
| Backend de traces | Tempo *(recommandé)*, Jaeger, Zipkin, Tempo + Jaeger |
| Mode de déploiement | Standalone, Multi-service |
| Backend de métriques | Prometheus *(recommandé)*, Mimir |
| Base de données | Aucune, PostgreSQL, MySQL, Oracle, H2 |
| Package de base | ex. `com.example.payment` |

**Modes de déploiement :**

- **Standalone** — le projet embarque sa propre stack d'observabilité complète (OTel Collector + métriques + Loki + Grafana). Idéal pour le développement solo ou les démos.
- **Multi-service** — le projet contient uniquement l'application. Il se connecte à une stack d'observabilité partagée lancée via `sbo init-obs`.

**Démarrage rapide :**

```bash
cd payment-service
docker compose -f docker/docker-compose.yml up -d
./mvnw spring-boot:run
```

| Endpoint | URL |
|----------|-----|
| Application | http://localhost:8080/actuator/health |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |
| Tempo | http://localhost:3200 |

---

#### Mode demo

```bash
sbo create payment-service --demo
```

Le flag `--demo` ajoute du code d'exemple fonctionnel au projet généré — idéal pour voir comment tout s'assemble avant d'écrire sa propre logique métier.

**Ce qui est ajouté :**

| Fichier | Démontre |
|---------|----------|
| `order/OrderController.java` (v1 + v2) | Endpoints REST, versioning d'API |
| `order/OrderService.java` | `@Observed` → span auto + timer Micrometer |
| `order/OrderExceptionHandler.java` | RFC 9457 `ProblemDetail`, logs d'erreur structurés |
| `payment/PaymentService.java` | `@Retryable` avec backoff exponentiel |
| `payment/PaymentService.java` | `@CircuitBreaker` avec fallback |
| `payment/ExternalPaymentGateway.java` | Dépendance externe défaillante simulée |
| `config/ResilienceConfig.java` | Active les proxies AOP Spring Retry |

**Endpoints pour générer de la télémétrie :**

```bash
# Rapide — visible dans Tempo + Prometheus
curl http://localhost:8080/api/v1/orders
curl http://localhost:8080/api/v1/orders/1
curl http://localhost:8080/api/v2/orders

# Déclenche un 404 + log warning avec trace_id → naviguer vers Loki → Tempo
curl http://localhost:8080/api/v1/orders/999

# Délai aléatoire 500ms–2s — observer le p95/p99 dans le dashboard HTTP
curl http://localhost:8080/api/v1/orders/slow

# @Retryable : échoue 2 fois, réussit au 3e essai — 3 spans dans Tempo
curl http://localhost:8080/api/v1/payment/authorize/1

# @CircuitBreaker : répéter pour ouvrir le circuit → retourne CIRCUIT_OPEN
curl http://localhost:8080/api/v1/payment/settle/1
```

---

#### `sbo init-obs`

Génère une **stack d'observabilité partagée** pour les architectures multi-services.
À lancer une seule fois, puis connecter autant de services que nécessaire.

```bash
sbo init-obs
```

**Questions interactives :**

| Question | Options |
|----------|---------|
| Backend de traces | Tempo, Jaeger, Zipkin, Tempo + Jaeger |
| Backend de métriques | Prometheus, Mimir |
| Dossier de sortie | `obs-stack` *(par défaut)* |

**Démarrage rapide :**

```bash
cd obs-stack
docker compose up -d
```

Tous les services rejoignant `obs-network` routeront automatiquement leur télémétrie vers cette stack.

---

### Architecture multi-service

```
┌─────────────────────────────────────────────────────────────┐
│                        obs-network                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ payment-svc  │  │  order-api   │  │  user-svc    │     │
│  │  :8080       │  │  :8081       │  │  :8082       │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         └─────────────────┴──────────────────┘             │
│                           │ OTLP :4318                      │
│                  ┌────────▼────────┐                        │
│                  │  OTel Collector │                        │
│                  └───┬──────┬──────┘                        │
│            Traces    │      │  Métriques + Logs             │
│          ┌───────────▼─┐  ┌─▼─────────────────┐            │
│          │    Tempo    │  │ Prometheus / Mimir │            │
│          └─────────────┘  │      + Loki        │            │
│                           └─────────┬──────────┘            │
│                          ┌──────────▼──────────┐            │
│                          │       Grafana        │            │
│                          └─────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**Mise en place :**

```bash
# 1. Lancer la stack obs partagée
sbo init-obs
cd obs-stack && docker compose up -d

# 2. Générer les services (mode multi-service)
sbo create payment-service   # choisir : Multi-service
sbo create order-api         # choisir : Multi-service

# 3. Démarrer chaque service
cd payment-service && APP_PORT=8080 docker compose -f docker/docker-compose.yml up -d
cd order-api       && APP_PORT=8081 docker compose -f docker/docker-compose.yml up -d
```

> Utilisez `APP_PORT` pour assigner un port hôte unique à chaque service et éviter les conflits.

---

### Versioning

| Tag | Spring Boot | Statut |
|-----|-------------|--------|
| `v1.0.x` | 4.0.x | **Actif** |
| `v1.1.x` | 4.1.x | À venir |

---

<div align="center">

Made with ☕ by [amaryange](https://github.com/amaryange) · [amarycode.dev](https://amarycode.dev)

</div>

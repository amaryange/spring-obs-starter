<div align="center">

```
 ____   ___  ____
/ ___| / _ \/ ___|
\___ \| | | \___ \
 ___) | |_| |___) |
|____/ \___/|____/
```

**Spring Boot 4 + OTel Observability Starter**

**Traces · Metrics · Logs — correlated out of the box**

[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.0.x-6DB33F?logo=springboot)](https://spring.io/projects/spring-boot)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-native-000?logo=opentelemetry)](https://opentelemetry.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[🇬🇧 English](#-english) · [🇫🇷 Français](#-français)


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
| Java | 17, 21 or 25 |
| Docker + Docker Compose | v2+ |

> `sos` is a standalone binary — no Python, no pip, no JDK required to run the generator itself.

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
| Linux x86_64 | `sos-linux-x86_64` |
| Linux arm64 | `sos-linux-arm64` |
| macOS x86_64 | `sos-macos-x86_64` |
| macOS arm64 (M1/M2/M3) | `sos-macos-arm64` |
| Windows x86_64 | `sos-windows-x86_64.exe` |

```bash
chmod +x sos-linux-x86_64
sudo mv sos-linux-x86_64 /usr/local/bin/sos
```

Verify:

```bash
sos
```

---

### Commands

#### `sos create <service-name>`

Generates a new Spring Boot 4 project from scratch.

```bash
sos create payment-service
```

Add `--demo` to include working example code (see [Demo mode](#demo-mode) below).

**Interactive questions:**

| Question | Options |
|----------|---------|
| Build tool | Maven *(recommended)*, Gradle Kotlin DSL |
| Java version | 21 LTS *(recommended)*, 25 (latest), 17 LTS |
| Trace backend | Tempo *(recommended)*, Jaeger, Zipkin, Tempo + Jaeger |
| Deployment mode | Standalone, Multi-service |
| Metrics backend | Prometheus *(recommended)*, Mimir |
| Database | None, PostgreSQL, MySQL, Oracle, H2 |
| Base package | e.g. `com.example.payment` |

**Deployment modes:**

- **Standalone** — the generated project embeds its own complete observability stack (OTel Collector + metrics + Loki + Grafana). Ideal for solo development or demos.
- **Multi-service** — the project contains only the application. It connects to a shared observability stack via `obs-network` (see [Multi-service architecture](#multi-service-architecture) below).

**Generated output:**

```
payment-service/
├── pom.xml                              # or build.gradle.kts
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
sos create payment-service --demo
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

#### `sos create-stack <stack-name>`

Generates a complete multi-service monorepo in one shot: a shared observability stack + N Spring Boot services, all wired together.

```bash
sos create-stack my-platform
```

**Interactive questions:**

| Question | Options |
|----------|---------|
| Build tool | Maven *(recommended)*, Gradle Kotlin DSL |
| Java version | 21 LTS *(recommended)*, 25 (latest), 17 LTS |
| Trace backend | Tempo *(recommended)*, Jaeger, Zipkin, Tempo + Jaeger |
| Metrics backend | Prometheus *(recommended)*, Mimir |
| Number of services | 1–20 |
| Per-service: name, database, package | — |
| `--demo` | Include demo controllers in each service |

**Generated output:**

```
my-platform/
├── obs-stack/                 # shared observability (OTel Collector, Loki, Grafana, …)
├── payment-service/           # Spring Boot app (multi-service mode)
├── order-api/                 # Spring Boot app (multi-service mode)
├── docker-compose.yml         # root orchestration (Docker Compose include:)
└── README.md
```

**Quick start:**

```bash
cd my-platform
docker compose up -d
```

Services are assigned sequential ports starting from `8080`.

---

### Multi-service architecture

For setups where multiple services share a single observability stack, you have two options:

**Option A — `sos create-stack`** *(recommended)*
Generates everything in one shot. See [`sos create-stack`](#sos-create-stack-stack-name) above.

**Option B — Download a pre-built obs stack + connect services manually**

Download a ready-to-use obs stack from [GitHub Releases](https://github.com/amaryange/spring-obs-starter/releases/latest):

| Archive | Backends |
|---------|----------|
| `obs-stack-tempo-prometheus.tar.gz` | Tempo + Prometheus *(recommended)* |
| `obs-stack-tempo-mimir.tar.gz` | Tempo + Mimir |
| `obs-stack-jaeger-prometheus.tar.gz` | Jaeger + Prometheus |
| `obs-stack-zipkin-prometheus.tar.gz` | Zipkin + Prometheus |

```bash
# 1. Extract and start the shared obs stack
tar xzf obs-stack-tempo-prometheus.tar.gz
cd obs-stack && docker compose up -d

# 2. Generate services (choose Multi-service mode)
sos create payment-service   # choose: Multi-service
sos create order-api         # choose: Multi-service

# 3. Start each service
cd payment-service && docker compose -f docker/docker-compose.yml up -d
cd order-api       && docker compose -f docker/docker-compose.yml up -d
```

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

> `sos` est un binaire standalone — aucune dépendance Python, pip ou JDK requise pour le générateur.

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
| Linux x86_64 | `sos-linux-x86_64` |
| Linux arm64 | `sos-linux-arm64` |
| macOS x86_64 | `sos-macos-x86_64` |
| macOS arm64 (M1/M2/M3) | `sos-macos-arm64` |
| Windows x86_64 | `sos-windows-x86_64.exe` |

```bash
chmod +x sos-linux-x86_64
sudo mv sos-linux-x86_64 /usr/local/bin/sos
```

Vérification :

```bash
sos
```

---

### Commandes

#### `sos create <nom-du-service>`

Génère un nouveau projet Spring Boot 4 de zéro.

```bash
sos create payment-service
```

Ajoutez `--demo` pour inclure du code d'exemple (voir [Mode demo](#mode-demo) ci-dessous).

**Questions interactives :**

| Question | Options |
|----------|---------|
| Outil de build | Maven *(recommandé)*, Gradle Kotlin DSL |
| Version Java | 21 LTS *(recommandé)*, 17 LTS |
| Backend de traces | Tempo *(recommandé)*, Jaeger, Zipkin, Tempo + Jaeger |
| Mode de déploiement | Standalone, Multi-service |
| Backend de métriques | Prometheus *(recommandé)*, Mimir |
| Base de données | Aucune, PostgreSQL, MySQL, Oracle, H2 |
| Package de base | ex. `com.example.payment` |

**Modes de déploiement :**

- **Standalone** — le projet embarque sa propre stack d'observabilité complète (OTel Collector + métriques + Loki + Grafana). Idéal pour le développement solo ou les démos.
- **Multi-service** — le projet contient uniquement l'application. Il se connecte à une stack d'observabilité partagée via `obs-network` (voir [Architecture multi-service](#architecture-multi-service) ci-dessous).

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
sos create payment-service --demo
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

#### `sos create-stack <nom-du-stack>`

Génère un monorepo multi-services complet en une seule commande : une stack d'observabilité partagée + N services Spring Boot, tout câblé ensemble.

```bash
sos create-stack my-platform
```

**Questions interactives :**

| Question | Options |
|----------|---------|
| Outil de build | Maven *(recommandé)*, Gradle Kotlin DSL |
| Version Java | 21 LTS *(recommandé)*, 17 LTS |
| Backend de traces | Tempo *(recommandé)*, Jaeger, Zipkin, Tempo + Jaeger |
| Backend de métriques | Prometheus *(recommandé)*, Mimir |
| Nombre de services | 1–20 |
| Par service : nom, base de données, package | — |
| `--demo` | Inclure les controllers de démo dans chaque service |

**Structure générée :**

```
my-platform/
├── obs-stack/                 # observabilité partagée (OTel Collector, Loki, Grafana, …)
├── payment-service/           # app Spring Boot (mode multi-service)
├── order-api/                 # app Spring Boot (mode multi-service)
├── docker-compose.yml         # orchestration racine (Docker Compose include:)
└── README.md
```

**Démarrage rapide :**

```bash
cd my-platform
docker compose up -d
```

Les services se voient attribuer des ports séquentiels à partir de `8080`.

---

### Architecture multi-service

Pour les setups où plusieurs services partagent une même stack d'observabilité, deux options :

**Option A — `sos create-stack`** *(recommandé)*
Génère tout en une seule commande. Voir [`sos create-stack`](#sos-create-stack-nom-du-stack) ci-dessus.

**Option B — Télécharger une obs-stack prébuilt + connecter les services manuellement**

Télécharger une obs-stack prête à l'emploi depuis [GitHub Releases](https://github.com/amaryange/spring-obs-starter/releases/latest) :

| Archive | Backends |
|---------|----------|
| `obs-stack-tempo-prometheus.tar.gz` | Tempo + Prometheus *(recommandé)* |
| `obs-stack-tempo-mimir.tar.gz` | Tempo + Mimir |
| `obs-stack-jaeger-prometheus.tar.gz` | Jaeger + Prometheus |
| `obs-stack-zipkin-prometheus.tar.gz` | Zipkin + Prometheus |

```bash
# 1. Extraire et démarrer la stack obs partagée
tar xzf obs-stack-tempo-prometheus.tar.gz
cd obs-stack && docker compose up -d

# 2. Générer les services (choisir le mode Multi-service)
sos create payment-service   # choisir : Multi-service
sos create order-api         # choisir : Multi-service

# 3. Démarrer chaque service
cd payment-service && docker compose -f docker/docker-compose.yml up -d
cd order-api       && docker compose -f docker/docker-compose.yml up -d
```

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
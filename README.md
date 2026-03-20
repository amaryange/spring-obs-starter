<div align="center">

```
 ___  ___  ___         █▀█ █▄▄ █▀
/ __|| _ )||_ )  ───  █▄█ █▄█ ▄█  Spring Boot 4 + OTel
\__ \| _ \ / /         Observability Starter
|___/|___//___|
```

**Traces · Metrics · Logs — correlated out of the box**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
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
| Python | 3.11+ |
| Java | 17 or 21 |
| Docker + Docker Compose | v2+ |
| pip | latest |

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

> No Python, no pip, no JDK required — `sbo` is a standalone binary.

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

**Interactive questions:**

| Question | Options |
|----------|---------|
| Build tool | Maven *(recommended)*, Gradle Kotlin DSL, Gradle Groovy DSL |
| Java version | 21 LTS *(recommended)*, 17 LTS |
| Trace backend | Tempo *(recommended)*, Jaeger, Zipkin, Tempo + Jaeger |
| Deployment mode | Standalone, Multi-service |
| Metrics backend | Prometheus *(recommended)*, Mimir |
| Target environment | Docker Compose, Kubernetes, Both |
| Database | None, PostgreSQL, MySQL, Oracle, H2 |
| Base package | e.g. `com.example.payment` |

**Deployment modes:**

- **Standalone** — the generated project embeds its own complete observability stack (OTel Collector + metrics + Loki + Grafana). Ideal for solo development or demos.
- **Multi-service** — the project only contains the application. It connects to a shared observability stack launched via `sbo init-obs`.

**Generated output:**

```
payment-service/
├── pom.xml                          # or build.gradle.kts / build.gradle
├── src/main/java/com/example/payment/
│   ├── PaymentServiceApplication.java
│   └── config/
│       └── OtelLogbackInstaller.java  # wires Logback → OTel Collector
├── src/main/resources/
│   ├── application.yml               # OTel + actuator config
│   └── logback-spring.xml            # Logback with OTel Appender
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

#### `sbo add [PATH...]`

Adds OTel observability wiring to **one or more existing Spring Boot 4 projects**.
**Non-destructive:** skips any file that already exists or is already configured.

```bash
# Single project (current directory)
sbo add .

# Explicit paths (polyrepo)
sbo add ~/services/payment-service ~/services/order-api

# Monorepo — auto-discovers Spring Boot projects one level deep
sbo add ~/my-platform/services/
```

**What it does:**

| Action | Condition |
|--------|-----------|
| Adds OTel deps to `pom.xml` / `build.gradle` | if not already present |
| Appends OTel block to `application.yml` | if `otlp` not already configured |
| Creates `OtelLogbackInstaller.java` | if file does not exist |
| Creates `logback-spring.xml` | if file does not exist |
| Generates `docker/docker-compose.yml` | if directory does not exist *(optional)* |

**Auto-detection:** build tool, service name, Java version, base package, Spring Boot version, database.

> ⚠️ If a `management:` key already exists in your `application.yml`, merge the appended block manually.

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
│         │                 │                  │              │
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

# Or add OTel to existing services
sbo add payment-service/ order-api/

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
| Python | 3.11+ |
| Java | 17 ou 21 |
| Docker + Docker Compose | v2+ |
| pip | dernière version |

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

> Aucune dépendance Python, pip ou JDK — `sbo` est un binaire standalone.

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

**Questions interactives :**

| Question | Options |
|----------|---------|
| Outil de build | Maven *(recommandé)*, Gradle Kotlin DSL, Gradle Groovy DSL |
| Version Java | 21 LTS *(recommandé)*, 17 LTS |
| Backend de traces | Tempo *(recommandé)*, Jaeger, Zipkin, Tempo + Jaeger |
| Mode de déploiement | Standalone, Multi-service |
| Backend de métriques | Prometheus *(recommandé)*, Mimir |
| Environnement cible | Docker Compose, Kubernetes, Les deux |
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

#### `sbo add [PATH...]`

Ajoute le câblage OTel à **un ou plusieurs projets Spring Boot 4 existants**.
**Non-destructif :** ignore les fichiers qui existent déjà ou sont déjà configurés.

```bash
# Projet courant
sbo add .

# Chemins explicites (polyrepo)
sbo add ~/services/payment-service ~/services/order-api

# Monorepo — auto-découverte des projets Spring Boot au niveau 1
sbo add ~/my-platform/services/
```

**Ce que ça fait :**

| Action | Condition |
|--------|-----------|
| Ajoute les dépendances OTel dans `pom.xml` / `build.gradle` | si absentes |
| Ajoute le bloc OTel dans `application.yml` | si `otlp` non configuré |
| Crée `OtelLogbackInstaller.java` | si le fichier n'existe pas |
| Crée `logback-spring.xml` | si le fichier n'existe pas |
| Génère `docker/docker-compose.yml` | si absent *(optionnel)* |

**Auto-détection :** outil de build, nom du service, version Java, package de base, version Spring Boot, base de données.

> ⚠️ Si une clé `management:` existe déjà dans `application.yml`, fusionner le bloc ajouté manuellement.

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

# Ou ajouter OTel à des services existants
sbo add payment-service/ order-api/

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

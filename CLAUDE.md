# CLAUDE.md — spring-obs-starter

## 🧠 Ton identité

Tu es un **développeur backend senior Java/Spring** avec **10 ans d'expérience** en production.
Tu as conçu et maintenu des architectures microservices pour des systèmes bancaires, fintech et cloud-native à fort trafic.
Tu connais Spring Boot dans ses moindres recoins — de l'autoconfiguration au contexte AOT, en passant par les subtilités de Micrometer et OpenTelemetry.

Tu n'écris **jamais** de code approximatif. Chaque fichier que tu produis doit pouvoir aller directement en production.
Tu anticipes les problèmes avant qu'ils arrivent. Tu documentes ce qui mérite d'être documenté. Tu ne laisses aucune configuration "magic" sans explication.

---

## 🎯 Objectif du projet

**spring-obs-starter** est un générateur CLI open source qui produit un projet Spring Boot **production-ready** avec une stack d'observabilité complète préconfigurée.

L'utilisateur lance **une seule commande**, répond à quelques questions interactives, et obtient un projet fonctionnel avec :
- OpenTelemetry natif Spring Boot 4 (`spring-boot-starter-opentelemetry`)
- Les 3 signaux corrélés : **Traces + Métriques + Logs** (trace_id injecté dans les logs)
- Choix du backend de traces : **Tempo** (recommandé), **Jaeger**, **Zipkin**, ou combinaison
- Choix de l'environnement cible : **Docker Compose** (dev local), **Kubernetes/K3s** (prod), ou les deux
- Dashboards Grafana pré-provisionnés, datasources auto-configurées

La **v1.0 cible exclusivement Spring Boot 4.0.x** — c'est la version de référence du projet.
Le support des versions antérieures (3.3.x, 3.4.x) pourra être ajouté dans des versions ultérieures si la demande communautaire le justifie.
Une nouvelle version du starter sera publiée à chaque nouvelle version stable de Spring Boot.

---

## 🏗️ Architecture du projet

```
spring-obs-starter/
│
├── cli/
│   ├── generate.py              ← CLI principal (Python + questionary)
│   ├── generator.py             ← logique de génération (Jinja2)
│   ├── models.py                ← dataclasses de config utilisateur
│   └── validators.py            ← validation des inputs
│
├── templates/
│   ├── spring-boot/
│   │   └── 4.0/                               ← seule version supportée en v1.0
│   │       ├── pom.xml.j2
│   │       ├── application.yml.j2
│   │       ├── logback-spring.xml.j2
│   │       ├── OtelLogbackInstaller.java.j2
│   │       └── MainApplication.java.j2
│   │
│   ├── docker/
│   │   ├── docker-compose.yml.j2
│   │   └── observability/
│   │       ├── otel-collector-config.yaml.j2  ← pipelines Traces/Metrics/Logs
│   │       ├── prometheus.yml.j2
│   │       ├── tempo.yaml                     ← si Tempo choisi
│   │       ├── jaeger/                        ← si Jaeger choisi
│   │       ├── zipkin/                        ← si Zipkin choisi
│   │       └── grafana/
│   │           └── provisioning/
│   │               ├── datasources/
│   │               │   └── datasources.yaml.j2
│   │               └── dashboards/
│   │                   ├── dashboard.yaml
│   │                   ├── jvm-dashboard.json
│   │                   ├── http-dashboard.json
│   │                   └── logs-traces-dashboard.json
│   │
│   └── k8s/
│       ├── namespace.yaml.j2
│       ├── app/
│       │   ├── deployment.yaml.j2
│       │   ├── service.yaml.j2
│       │   ├── configmap.yaml.j2
│       │   └── hpa.yaml.j2
│       └── observability/
│           ├── otel-collector/
│           ├── tempo/
│           ├── prometheus/
│           ├── loki/
│           └── grafana/
│
├── tests/
│   ├── test_generator.py
│   └── test_cli.py
│
├── CHANGELOG.md
├── README.md
└── pyproject.toml
```

---

## ⚙️ Stack technique

### CLI
- **Python 3.11+**
- `questionary` — interface CLI interactive (prompts, sélection, multi-select)
- `Jinja2` — templating pour tous les fichiers générés
- `rich` — affichage console (spinners, couleurs, tableaux)
- `click` — parsing des arguments CLI

### Templates Spring Boot 4 (stack principale)
- `spring-boot-starter-opentelemetry` — **starter natif officiel SB4** (inclut OTel API + Micrometer bridge + OTLP exporters)
- `spring-boot-starter-actuator` — health checks, métriques Prometheus endpoint
- `spring-boot-docker-compose` — auto-config LGTM en dev
- `opentelemetry-logback-appender-1.0` — pont Logback → OTel Collector (logs)
- Java 21 (LTS) par défaut, Java 17 supporté

### Stack observabilité
| Signal   | Collecte                        | Backend              | Visualisation |
|----------|---------------------------------|----------------------|---------------|
| Traces   | OTel Collector (OTLP 4317/4318) | Tempo / Jaeger / Zipkin | Grafana       |
| Métriques| Prometheus scrape `/actuator/prometheus` + OTLP push | Prometheus / Mimir | Grafana |
| Logs     | Logback OTel Appender → OTLP   | Loki                 | Grafana       |

**La corrélation trace_id** entre les 3 signaux est le différenciateur central du starter.

---

## 🔑 Règles techniques absolues

### Spring Boot 4 — OpenTelemetry natif

1. **Toujours utiliser `spring-boot-starter-opentelemetry`** — jamais l'ancien `opentelemetry-spring-boot-starter` communautaire ni le Java agent pour SB4.

2. **Version minimale : 4.0.1** — la 4.0.0 a des bugs sur l'export des logs OTLP.

3. **Le Logback OTel Appender n'est pas auto-installé par SB4** — il faut TOUJOURS inclure :
    - La dépendance `opentelemetry-logback-appender-1.0`
    - Le `logback-spring.xml` avec l'appender déclaré
    - Le bean `OtelLogbackInstaller` qui appelle `OpenTelemetryAppender.install(openTelemetry)`
      Sans ces 3 éléments, les logs ne partent pas dans Loki et la corrélation trace_id est cassée.

4. **Port 4318 (HTTP) par défaut** pour l'export OTLP dans les templates. Port 4317 (gRPC) en option avancée.

5. **`@Observed` sur les méthodes métier critiques** — SB4 génère automatiquement un span + une métrique Micrometer. Documenter ce comportement dans le README généré.

6. **Sampling probability** :
    - `1.0` en dev/local (Docker Compose)
    - `0.1` en staging
    - `0.05` à `0.1` en prod (configurable via `OTEL_SAMPLING_PROBABILITY`)

### OTel Collector

7. **Toujours passer par l'OTel Collector** — ne jamais exporter directement de l'app vers Tempo/Jaeger/Prometheus. Le Collector permet de changer de backend sans toucher à l'app.

8. **Pipelines séparés** dans `otel-collector-config.yaml` pour chaque signal (traces, metrics, logs) — ne jamais mélanger dans un seul pipeline.

9. **Batch processor obligatoire** — ne jamais utiliser le `direct` exporter en production (surcharge réseau).

### Docker Compose

10. **`depends_on` avec `condition: service_healthy`** sur tous les services observabilité — évite les race conditions au démarrage.

11. **Health checks** définis sur Prometheus, Loki, Tempo/Jaeger, Grafana et OTel Collector.

12. **Volumes nommés** pour la persistance Grafana et Prometheus — jamais de bind mounts relatifs en prod.

### Kubernetes

13. **Namespace dédié `observability`** séparé du namespace applicatif.

14. **Resources requests/limits** sur tous les pods observabilité — ne jamais laisser sans limites.

15. **ConfigMaps pour toutes les configurations** OTel Collector, Prometheus, Grafana provisioning — jamais en dur dans les images.

16. **HPA** (HorizontalPodAutoscaler) généré pour l'application, basé sur CPU + métriques custom via Prometheus adapter.

### Qualité générale

17. **Variables d'environnement pour TOUT ce qui peut changer** entre dev/staging/prod — endpoint OTLP, sampling rate, service name, etc.

18. **Pas de credentials en dur** dans aucun fichier généré — utiliser des placeholders `${VARIABLE:default_value}`.

19. **Chaque fichier généré doit être valide et fonctionnel tel quel** — l'utilisateur ne doit pas avoir à modifier quoi que ce soit pour démarrer.

20. **Les dashboards Grafana pré-provisionnés** doivent inclure :
    - JVM Dashboard (heap, GC, threads, CPU)
    - HTTP Dashboard (latence p50/p95/p99, taux d'erreur, throughput)
    - Logs + Traces corrélés (lien direct Loki → Tempo depuis les logs)

---

## 📋 Comportement du CLI

### Commandes
```bash
sos create <service-name>           # nouveau projet solo
sos create-stack <stack-name>       # stack multi-services (obs partagée + N services)
sos --version                       # affiche la version CLI + Spring Boot embarqué
```

### Questions posées dans l'ordre (`sos create`)
```
1. Spring Boot version  → [4.0.5 (latest) | 4.0.4 | 4.0.3 | 4.0.2 | 4.0.1]
2. Build tool           → [Maven (recommandé) | Gradle — Kotlin DSL]
3. Java version         → [21 LTS (recommandé) | 25 (latest) | 17 LTS]
4. Backend de traces    → [Tempo | Jaeger | Zipkin | Tempo + Jaeger]
5. Deployment mode      → [Standalone | Multi-service]
6. Metrics backend      → [Prometheus (recommandé) | Mimir]  ← si Standalone
7. Database             → [None | PostgreSQL | MySQL | Oracle | H2]
8. Package de base      → (input libre, ex: com.monentreprise.payment)
```

### Output attendu
```
✔ Generating Spring Boot 4.0.5 project...
✔ Configuring OpenTelemetry native starter...
✔ Setting up OTel Collector pipelines (traces → Tempo, metrics → Prometheus, logs → Loki)...
✔ Wiring Logback OTel Appender for log correlation...
✔ Generating Docker Compose stack with health checks...
✔ Provisioning Grafana dashboards (JVM, HTTP, Logs-Traces)...
✔ Writing README with quick start guide...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Project ready: ./my-payment-service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Quick start:
  $ cd my-payment-service
  $ docker compose up -d
  $ ./mvnw spring-boot:run

  Grafana    → http://localhost:3000  (admin/admin)
  Prometheus → http://localhost:9090
  Tempo      → http://localhost:3200
  Loki       → http://localhost:3100
  App        → http://localhost:8080/actuator/health
```

---

## 🔄 Stratégie de versioning

### Branches
```
main              → documentation, README global
develop           → travail en cours
release/4.0       → ligne Spring Boot 4.0.x  ← actuelle
release/4.1       → ligne Spring Boot 4.1.x  (future)
```

### Tags (releases GitHub)
| Branche          | Tag       | Spring Boot | Statut      |
|------------------|-----------|-------------|-------------|
| `release/4.0`    | `v1.0.5`  | 4.0.5       | **Actif**   |
| `release/4.1`    | `v1.1.0`  | 4.1.0       | À venir     |
| `release/5.0`    | `v2.0.0`  | 5.0.0       | Futur       |

**Workflow lors d'une nouvelle version Spring Boot :**
1. Nouvelle GA Spring Boot 4.0.x → on travaille sur `release/4.0`
2. On met à jour `SPRING_BOOT_VERSION` + `SUPPORTED_SPRING_BOOT_VERSIONS` dans `models.py`
3. On bumpe la version dans `pyproject.toml`
4. On tag → release GitHub + binaire automatiquement via CI

> Support Spring Boot 3.x : hors scope v1.0.

- Une **nouvelle version mineure** à chaque nouvelle version mineure de Spring Boot.
- Une **nouvelle version majeure** à chaque nouvelle version majeure de Spring Boot.
- Le `CHANGELOG.md` documente systématiquement les changements de dépendances OTel et Spring.

---

## 🚫 Ce qu'il ne faut JAMAIS faire

- ❌ Utiliser le **Java agent OTel** (`-javaagent`) dans les templates SB4 — incompatible avec GraalVM native, conflits possibles avec d'autres agents.
- ❌ Exporter les métriques **uniquement via OTLP push** sans exposer `/actuator/prometheus` — certains environnements ne supportent que le scrape Prometheus.
- ❌ Mettre `management.endpoints.web.exposure.include=*` — exposer uniquement ce qui est nécessaire.
- ❌ Utiliser `spring.profiles.active` dans les fichiers générés — laisser l'utilisateur gérer ses profils.
- ❌ Oublier le **`OtelLogbackInstaller` bean** — sans lui, les logs n'ont pas de trace_id et la corrélation est cassée.
- ❌ Générer des fichiers K8s sans `resources.requests` et `resources.limits` — c'est un anti-pattern de production.
- ❌ Laisser Grafana avec les credentials par défaut sans avertissement — toujours indiquer dans le README de les changer en prod.

---

## 📚 Références

- [Spring Blog — OpenTelemetry with Spring Boot (Nov 2025)](https://spring.io/blog/2025/11/18/opentelemetry-with-spring-boot/)
- [Spring Boot 4 Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [Grafana LGTM Stack](https://grafana.com/go/webinar/getting-started-with-grafana-lgtm-stack/)
- [Micrometer Observation API](https://micrometer.io/docs/observation)
- [OTel Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
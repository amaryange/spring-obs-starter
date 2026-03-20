import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from cli.models import ProjectConfig, TargetEnvironment, Database, MetricsBackend

# Resolved at import time — templates/ lives next to cli/ in the repo root
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class ProjectGenerator:
    """
    Renders Jinja2 templates and copies static files into the output directory.

    Template naming convention:
      - *.j2  → rendered with Jinja2, .j2 suffix stripped in output
      - other → copied as-is (static files: dashboards, loki.yml, tempo.yml, …)
    """

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            keep_trailing_newline=True,
            autoescape=False,
            undefined=StrictUndefined,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, config: ProjectConfig, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for template_path, output_path in self._build_manifest(config):
            full_output = output_dir / output_path
            full_output.parent.mkdir(parents=True, exist_ok=True)
            if template_path.endswith(".j2"):
                self._render(config, template_path, full_output)
            else:
                self._copy(template_path, full_output)

    # ------------------------------------------------------------------
    # File manifest
    # ------------------------------------------------------------------

    def _build_manifest(self, config: ProjectConfig) -> list[tuple[str, str]]:
        """Returns (template_path_relative_to_templates_dir, output_path) pairs."""
        pkg = config.package_path
        cls = config.class_name
        files: list[tuple[str, str]] = []

        # --- Build descriptor ---
        if config.use_maven:
            files.append(("spring-boot/4.0/pom.xml.j2", "pom.xml"))
        elif config.use_gradle_kotlin:
            files += [
                ("spring-boot/4.0/build.gradle.kts.j2", "build.gradle.kts"),
                ("spring-boot/4.0/settings.gradle.kts.j2", "settings.gradle.kts"),
            ]
        else:  # Gradle Groovy
            files += [
                ("spring-boot/4.0/build.gradle.j2", "build.gradle"),
                ("spring-boot/4.0/settings.gradle.j2", "settings.gradle"),
            ]

        # --- Spring Boot application ---
        files += [
            (
                "spring-boot/4.0/application.yml.j2",
                "src/main/resources/application.yml",
            ),
            (
                "spring-boot/4.0/logback-spring.xml",
                "src/main/resources/logback-spring.xml",
            ),
            (
                "spring-boot/4.0/MainApplication.java.j2",
                f"src/main/java/{pkg}/{cls}Application.java",
            ),
            (
                "spring-boot/4.0/OtelLogbackInstaller.java.j2",
                f"src/main/java/{pkg}/config/OtelLogbackInstaller.java",
            ),
        ]

        # Database migration skeleton
        if config.use_database and config.database != Database.ORACLE:
            files.append((
                f"spring-boot/4.0/db/V1__init.{config.database.value}.sql",
                "src/main/resources/db/migration/V1__init.sql",
            ))
        elif config.database == Database.ORACLE:
            files.append((
                "spring-boot/4.0/db/V1__init.oracle.sql",
                "src/main/resources/db/migration/V1__init.sql",
            ))

        # --- Docker Compose stack ---
        if config.use_docker:
            files += [
                (
                    "docker/docker-compose.yml.j2",
                    "docker/docker-compose.yml",
                ),
                (
                    "docker/observability/otel-collector/otel-collector.yml.j2",
                    "docker/observability/otel-collector/otel-collector.yml",
                ),
                *(
                    [(
                        "docker/observability/prometheus/prometheus.yml.j2",
                        "docker/observability/prometheus/prometheus.yml",
                    )]
                    if config.use_prometheus else
                    [(
                        "docker/observability/mimir/mimir.yml",
                        "docker/observability/mimir/mimir.yml",
                    )]
                ),
                (
                    "docker/observability/loki/loki.yml",
                    "docker/observability/loki/loki.yml",
                ),
                (
                    "docker/observability/grafana/provisioning/datasources/datasources.yaml.j2",
                    "docker/observability/grafana/provisioning/datasources/datasources.yml",
                ),
                (
                    "docker/observability/grafana/provisioning/dashboards/dashboards.yml",
                    "docker/observability/grafana/provisioning/dashboards/dashboards.yml",
                ),
                # Static dashboard JSONs — copied as-is
                (
                    "docker/observability/grafana/provisioning/dashboards/jvm-dashboard.json",
                    "docker/observability/grafana/provisioning/dashboards/jvm-dashboard.json",
                ),
                (
                    "docker/observability/grafana/provisioning/dashboards/http-dashboard.json",
                    "docker/observability/grafana/provisioning/dashboards/http-dashboard.json",
                ),
                (
                    "docker/observability/grafana/provisioning/dashboards/logs-traces-dashboard.json",
                    "docker/observability/grafana/provisioning/dashboards/logs-traces-dashboard.json",
                ),
            ]

            if config.use_tempo:
                files.append((
                    "docker/observability/tempo/tempo.yml.j2",
                    "docker/observability/tempo/tempo.yml",
                ))

        # --- README ---
        files.append(("README.md.j2", "README.md"))

        return files

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render(self, config: ProjectConfig, template_path: str, output: Path) -> None:
        template = self.env.get_template(template_path)
        output.write_text(template.render(config=config), encoding="utf-8")

    def _copy(self, template_path: str, output: Path) -> None:
        src = self.templates_dir / template_path
        shutil.copy2(src, output)

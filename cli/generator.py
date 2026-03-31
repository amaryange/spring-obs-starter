import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from dataclasses import replace

from cli.models import ProjectConfig, TargetEnvironment, Database, MetricsBackend, DeploymentMode, StackConfig


def _get_templates_dir() -> Path:
    """
    Resolve the templates directory whether running from source or as a
    PyInstaller one-file binary (sys._MEIPASS points to the temp bundle dir).
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "templates"
    return Path(__file__).parent.parent / "templates"


TEMPLATES_DIR = _get_templates_dir()


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

    _EXECUTABLES = {"mvnw", "gradlew"}

    def generate(self, config: ProjectConfig, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for template_path, output_path in self._build_manifest(config):
            full_output = output_dir / output_path
            full_output.parent.mkdir(parents=True, exist_ok=True)
            if template_path.endswith(".j2"):
                self._render(config, template_path, full_output)
            else:
                self._copy(template_path, full_output)
            if full_output.name in self._EXECUTABLES:
                full_output.chmod(full_output.stat().st_mode | 0o111)

    # ------------------------------------------------------------------
    # File manifest
    # ------------------------------------------------------------------

    def _build_manifest(self, config: ProjectConfig) -> list[tuple[str, str]]:
        """Returns (template_path_relative_to_templates_dir, output_path) pairs."""
        pkg = config.package_path
        cls = config.class_name
        files: list[tuple[str, str]] = []

        # --- Build descriptor + wrapper ---
        if config.use_maven:
            files += [
                ("spring-boot/4.0/pom.xml.j2", "pom.xml"),
                ("spring-boot/4.0/wrapper/maven/mvnw", "mvnw"),
                ("spring-boot/4.0/wrapper/maven/mvnw.cmd", "mvnw.cmd"),
                ("spring-boot/4.0/wrapper/maven/.mvn/wrapper/maven-wrapper.properties",
                 ".mvn/wrapper/maven-wrapper.properties"),
            ]
        elif config.use_gradle_kotlin:
            files += [
                ("spring-boot/4.0/build.gradle.kts.j2", "build.gradle.kts"),
                ("spring-boot/4.0/settings.gradle.kts.j2", "settings.gradle.kts"),
                ("spring-boot/4.0/wrapper/gradle/gradlew", "gradlew"),
                ("spring-boot/4.0/wrapper/gradle/gradlew.bat", "gradlew.bat"),
                ("spring-boot/4.0/wrapper/gradle/gradle/wrapper/gradle-wrapper.properties",
                 "gradle/wrapper/gradle-wrapper.properties"),
                ("spring-boot/4.0/wrapper/gradle/gradle/wrapper/gradle-wrapper.jar",
                 "gradle/wrapper/gradle-wrapper.jar"),
            ]

        # --- Dockerfile ---
        files.append(("spring-boot/4.0/Dockerfile.j2", "Dockerfile"))

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

        # --- Database migration skeleton ---
        if config.use_database:
            files.append((
                f"spring-boot/4.0/db/V1__init.{config.database.value}.sql",
                "src/main/resources/db/migration/V1__init.sql",
            ))

        # --- Demo code (@Observed, @Retryable, @CircuitBreaker) ---
        if config.demo:
            files += self._demo_files(config)

        # --- Docker Compose stack ---
        if config.use_docker:
            if config.is_standalone:
                files += self._standalone_docker_files(config)
            else:
                files.append((
                    "docker/docker-compose.service.yml.j2",
                    "docker/docker-compose.yml",
                ))

        # --- README ---
        files.append(("README.md.j2", "README.md"))

        return files

    def _standalone_docker_files(self, config: ProjectConfig) -> list[tuple[str, str]]:
        """All files needed for the standalone (app + full obs stack) compose mode."""
        files: list[tuple[str, str]] = [
            (
                "docker/docker-compose.standalone.yml.j2",
                "docker/docker-compose.yml",
            ),
            (
                "docker/observability/otel-collector/otel-collector.yml.j2",
                "docker/observability/otel-collector/otel-collector.yml",
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

        if config.use_prometheus:
            files.append((
                "docker/observability/prometheus/prometheus.yml.j2",
                "docker/observability/prometheus/prometheus.yml",
            ))
        else:
            files.append((
                "docker/observability/mimir/mimir.yml",
                "docker/observability/mimir/mimir.yml",
            ))

        if config.use_tempo:
            files.append((
                "docker/observability/tempo/tempo.yml.j2",
                "docker/observability/tempo/tempo.yml",
            ))

        return files

    # ------------------------------------------------------------------
    # Demo files (@Observed, @Retryable, @CircuitBreaker examples)
    # ------------------------------------------------------------------

    def _demo_files(self, config: ProjectConfig) -> list[tuple[str, str]]:
        pkg = config.package_path
        d = "spring-boot/4.0/demo"
        return [
            (f"{d}/config/ResilienceConfig.java.j2",        f"src/main/java/{pkg}/config/ResilienceConfig.java"),
            (f"{d}/order/Order.java.j2",                     f"src/main/java/{pkg}/order/Order.java"),
            (f"{d}/order/OrderNotFoundException.java.j2",    f"src/main/java/{pkg}/order/OrderNotFoundException.java"),
            (f"{d}/order/OrderExceptionHandler.java.j2",     f"src/main/java/{pkg}/order/OrderExceptionHandler.java"),
            (f"{d}/order/OrderService.java.j2",              f"src/main/java/{pkg}/order/OrderService.java"),
            (f"{d}/order/OrderController.java.j2",           f"src/main/java/{pkg}/order/OrderController.java"),
            (f"{d}/order/v2/OrderResponseV2.java.j2",        f"src/main/java/{pkg}/order/v2/OrderResponseV2.java"),
            (f"{d}/order/v2/OrderControllerV2.java.j2",      f"src/main/java/{pkg}/order/v2/OrderControllerV2.java"),
            (f"{d}/payment/PaymentGatewayException.java.j2", f"src/main/java/{pkg}/payment/PaymentGatewayException.java"),
            (f"{d}/payment/PaymentResult.java.j2",           f"src/main/java/{pkg}/payment/PaymentResult.java"),
            (f"{d}/payment/ExternalPaymentGateway.java.j2",  f"src/main/java/{pkg}/payment/ExternalPaymentGateway.java"),
            (f"{d}/payment/PaymentService.java.j2",          f"src/main/java/{pkg}/payment/PaymentService.java"),
            (f"{d}/payment/PaymentController.java.j2",       f"src/main/java/{pkg}/payment/PaymentController.java"),
        ]

    # ------------------------------------------------------------------
    # init-obs: shared observability stack
    # ------------------------------------------------------------------

    def generate_obs_stack(
        self,
        config: "ProjectConfig",
        output_dir: Path,
        stack_config: "StackConfig | None" = None,
    ) -> None:
        """Generate a standalone shared obs stack (no app service)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        for template_path, output_path in self._obs_manifest(config):
            full_output = output_dir / output_path
            full_output.parent.mkdir(parents=True, exist_ok=True)
            if template_path.endswith(".j2"):
                if stack_config is not None and "prometheus.yml.j2" in template_path:
                    self._render_with_context(
                        {"config": config, "stack": stack_config},
                        template_path,
                        full_output,
                    )
                else:
                    self._render(config, template_path, full_output)
            else:
                self._copy(template_path, full_output)

    def generate_stack(self, stack_config: "StackConfig", output_dir: Path) -> None:
        """Generate a complete multi-service stack: obs-stack + N services + root compose."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Shared obs stack (prometheus gets per-service scrape targets)
        obs_config = ProjectConfig.for_obs_stack(
            trace_backend=stack_config.trace_backend,
            metrics_backend=stack_config.metrics_backend,
        )
        self.generate_obs_stack(obs_config, output_dir / "obs-stack", stack_config=stack_config)

        # 2. Per-service projects (always MULTI_SERVICE deployment mode)
        for svc in stack_config.services:
            svc_config = replace(svc, deployment_mode=DeploymentMode.MULTI_SERVICE)
            self.generate(svc_config, output_dir / svc_config.artifact_id)

        # 3. Root docker-compose.yml
        self._render_with_context(
            {"stack": stack_config},
            "docker/docker-compose.root.yml.j2",
            output_dir / "docker-compose.yml",
        )

        # 4. Root README.md
        self._render_with_context(
            {"stack": stack_config},
            "README.stack.md.j2",
            output_dir / "README.md",
        )

    def _obs_manifest(self, config: "ProjectConfig") -> list[tuple[str, str]]:
        files: list[tuple[str, str]] = [
            (
                "docker/docker-compose.obs.yml.j2",
                "docker-compose.yml",
            ),
            (
                "docker/observability/otel-collector/otel-collector.yml.j2",
                "observability/otel-collector/otel-collector.yml",
            ),
            (
                "docker/observability/loki/loki.yml",
                "observability/loki/loki.yml",
            ),
            (
                "docker/observability/grafana/provisioning/datasources/datasources.yaml.j2",
                "observability/grafana/provisioning/datasources/datasources.yml",
            ),
            (
                "docker/observability/grafana/provisioning/dashboards/dashboards.yml",
                "observability/grafana/provisioning/dashboards/dashboards.yml",
            ),
            (
                "docker/observability/grafana/provisioning/dashboards/jvm-dashboard.json",
                "observability/grafana/provisioning/dashboards/jvm-dashboard.json",
            ),
            (
                "docker/observability/grafana/provisioning/dashboards/http-dashboard.json",
                "observability/grafana/provisioning/dashboards/http-dashboard.json",
            ),
            (
                "docker/observability/grafana/provisioning/dashboards/logs-traces-dashboard.json",
                "observability/grafana/provisioning/dashboards/logs-traces-dashboard.json",
            ),
        ]

        if config.use_prometheus:
            files.append((
                "docker/observability/prometheus/prometheus.yml.j2",
                "observability/prometheus/prometheus.yml",
            ))
        else:
            files.append((
                "docker/observability/mimir/mimir.yml",
                "observability/mimir/mimir.yml",
            ))

        if config.use_tempo:
            files.append((
                "docker/observability/tempo/tempo.yml.j2",
                "observability/tempo/tempo.yml",
            ))

        return files

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render(self, config: ProjectConfig, template_path: str, output: Path) -> None:
        template = self.env.get_template(template_path)
        output.write_text(template.render(config=config), encoding="utf-8")

    def _render_with_context(self, context: dict, template_path: str, output: Path) -> None:
        template = self.env.get_template(template_path)
        output.write_text(template.render(**context), encoding="utf-8")

    def _copy(self, template_path: str, output: Path) -> None:
        src = self.templates_dir / template_path
        shutil.copy2(src, output)
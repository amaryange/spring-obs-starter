"""Tests for ProjectGenerator — manifest, file creation, template rendering."""
import pytest
from pathlib import Path

from cli.generator import ProjectGenerator
from cli.models import (
    BuildTool,
    Database,
    DeploymentMode,
    JavaVersion,
    MetricsBackend,
    ProjectConfig,
    TargetEnvironment,
    TraceBackend,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _config(**overrides) -> ProjectConfig:
    base = dict(
        service_name="payment-service",
        base_package="com.example.payment",
        java_version=JavaVersion.V21,
        trace_backend=TraceBackend.TEMPO,
        environment=TargetEnvironment.DOCKER_COMPOSE,
        database=Database.NONE,
        build_tool=BuildTool.MAVEN,
        metrics_backend=MetricsBackend.PROMETHEUS,
        deployment_mode=DeploymentMode.STANDALONE,
        spring_boot_version="4.0.5",
    )
    base.update(overrides)
    return ProjectConfig(**base)


@pytest.fixture
def generator() -> ProjectGenerator:
    return ProjectGenerator()


@pytest.fixture
def standalone_config() -> ProjectConfig:
    return _config()


@pytest.fixture
def multi_service_config() -> ProjectConfig:
    return _config(deployment_mode=DeploymentMode.MULTI_SERVICE)


# ---------------------------------------------------------------------------
# ProjectConfig — derived properties
# ---------------------------------------------------------------------------

class TestProjectConfig:
    def test_artifact_id_kebab(self):
        assert _config(service_name="MyPayment").artifact_id == "mypayment"
        assert _config(service_name="my_service").artifact_id == "my-service"

    def test_class_name_pascal(self):
        assert _config(service_name="payment-service").class_name == "PaymentService"
        assert _config(service_name="order").class_name == "Order"

    def test_package_path(self):
        cfg = _config(base_package="com.example.payment")
        assert cfg.package_path == "com/example/payment"

    def test_use_tempo(self):
        assert _config(trace_backend=TraceBackend.TEMPO).use_tempo is True
        assert _config(trace_backend=TraceBackend.TEMPO_JAEGER).use_tempo is True
        assert _config(trace_backend=TraceBackend.JAEGER).use_tempo is False
        assert _config(trace_backend=TraceBackend.ZIPKIN).use_tempo is False

    def test_use_jaeger(self):
        assert _config(trace_backend=TraceBackend.JAEGER).use_jaeger is True
        assert _config(trace_backend=TraceBackend.TEMPO_JAEGER).use_jaeger is True
        assert _config(trace_backend=TraceBackend.TEMPO).use_jaeger is False

    def test_use_zipkin(self):
        assert _config(trace_backend=TraceBackend.ZIPKIN).use_zipkin is True
        assert _config(trace_backend=TraceBackend.TEMPO).use_zipkin is False

    def test_use_prometheus(self):
        assert _config(metrics_backend=MetricsBackend.PROMETHEUS).use_prometheus is True
        assert _config(metrics_backend=MetricsBackend.MIMIR).use_prometheus is False

    def test_use_database(self):
        assert _config(database=Database.NONE).use_database is False
        assert _config(database=Database.POSTGRESQL).use_database is True

    def test_datasource_url_postgresql(self):
        url = _config(database=Database.POSTGRESQL).datasource_url
        assert "jdbc:postgresql" in url
        assert "5432" in url

    def test_datasource_url_mysql(self):
        url = _config(database=Database.MYSQL).datasource_url
        assert "jdbc:mysql" in url
        assert "3306" in url

    def test_build_command_maven(self):
        assert _config(build_tool=BuildTool.MAVEN).build_command == "./mvnw spring-boot:run"

    def test_build_command_gradle(self):
        assert _config(build_tool=BuildTool.GRADLE_KOTLIN).build_command == "./gradlew bootRun"


# ---------------------------------------------------------------------------
# Manifest — file list correctness
# ---------------------------------------------------------------------------

class TestManifest:
    def _templates(self, config: ProjectConfig) -> list[str]:
        return [t for t, _ in ProjectGenerator()._build_manifest(config)]

    def _outputs(self, config: ProjectConfig) -> list[str]:
        return [o for _, o in ProjectGenerator()._build_manifest(config)]

    def test_maven_files_present(self, standalone_config):
        templates = self._templates(standalone_config)
        assert any("pom.xml.j2" in t for t in templates)
        assert any("mvnw" in t for t in templates)
        assert not any("build.gradle" in t for t in templates)

    def test_gradle_files_present(self):
        cfg = _config(build_tool=BuildTool.GRADLE_KOTLIN)
        templates = self._templates(cfg)
        assert any("build.gradle.kts.j2" in t for t in templates)
        assert any("gradlew" in t for t in templates)
        assert not any("pom.xml" in t for t in templates)

    def test_spring_boot_files_always_present(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert "src/main/resources/application.yml" in outputs
        assert "src/main/resources/logback-spring.xml" in outputs
        assert "Dockerfile" in outputs

    def test_otel_installer_always_present(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert any("OtelLogbackInstaller.java" in o for o in outputs)

    def test_standalone_includes_obs_stack(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert "docker/docker-compose.yml" in outputs
        assert any("otel-collector.yml" in o for o in outputs)
        assert any("datasources.yml" in o for o in outputs)
        assert any("jvm-dashboard.json" in o for o in outputs)

    def test_multi_service_only_service_compose(self, multi_service_config):
        outputs = self._outputs(multi_service_config)
        assert "docker/docker-compose.yml" in outputs
        assert not any("otel-collector" in o for o in outputs)
        assert not any("grafana" in o for o in outputs)

    def test_prometheus_included_when_selected(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert any("prometheus.yml" in o for o in outputs)
        assert not any("mimir.yml" in o for o in outputs)

    def test_mimir_included_when_selected(self):
        cfg = _config(metrics_backend=MetricsBackend.MIMIR)
        outputs = self._outputs(cfg)
        assert any("mimir.yml" in o for o in outputs)
        assert not any("prometheus.yml" in o for o in outputs)

    def test_tempo_included_when_selected(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert any("tempo.yml" in o for o in outputs)

    def test_tempo_absent_for_jaeger(self):
        cfg = _config(trace_backend=TraceBackend.JAEGER)
        outputs = self._outputs(cfg)
        assert not any("tempo.yml" in o for o in outputs)

    def test_db_migration_postgresql(self):
        cfg = _config(database=Database.POSTGRESQL)
        outputs = self._outputs(cfg)
        assert "src/main/resources/db/migration/V1__init.sql" in outputs

    def test_no_db_migration_when_none(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert not any("db/migration" in o for o in outputs)

    def test_demo_files_when_enabled(self):
        cfg = _config(demo=True)
        outputs = self._outputs(cfg)
        assert any("OrderController.java" in o for o in outputs)
        assert any("PaymentService.java" in o for o in outputs)

    def test_no_demo_files_by_default(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert not any("OrderController.java" in o for o in outputs)

    def test_readme_always_present(self, standalone_config):
        outputs = self._outputs(standalone_config)
        assert "README.md" in outputs


# ---------------------------------------------------------------------------
# Generator — actual file creation on disk
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_creates_output_directory(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        assert out.is_dir()

    def test_pom_xml_contains_service_name(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        pom = (out / "pom.xml").read_text()
        assert "payment-service" in pom
        assert "4.0.5" in pom

    def test_pom_xml_contains_java_version(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        pom = (out / "pom.xml").read_text()
        assert "<java.version>21</java.version>" in pom

    def test_application_yml_contains_service_name(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        yml = (out / "src/main/resources/application.yml").read_text()
        assert "payment-service" in yml

    def test_main_application_java_created(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        java = out / "src/main/java/com/example/payment/PaymentServiceApplication.java"
        assert java.exists()
        assert "PaymentServiceApplication" in java.read_text()

    def test_otel_installer_java_created(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        installer = out / "src/main/java/com/example/payment/config/OtelLogbackInstaller.java"
        assert installer.exists()
        assert "OpenTelemetryAppender" in installer.read_text()

    def test_mvnw_is_executable(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        mvnw = out / "mvnw"
        assert mvnw.exists()
        assert mvnw.stat().st_mode & 0o111

    def test_gradle_build_file_created(self, tmp_path, generator):
        cfg = _config(build_tool=BuildTool.GRADLE_KOTLIN)
        out = tmp_path / "payment-service"
        generator.generate(cfg, out)
        assert (out / "build.gradle.kts").exists()
        assert not (out / "pom.xml").exists()

    def test_docker_compose_created_standalone(self, tmp_path, generator, standalone_config):
        out = tmp_path / "payment-service"
        generator.generate(standalone_config, out)
        assert (out / "docker/docker-compose.yml").exists()
        assert (out / "docker/observability/otel-collector/otel-collector.yml").exists()

    def test_no_obs_stack_for_multi_service(self, tmp_path, generator, multi_service_config):
        out = tmp_path / "payment-service"
        generator.generate(multi_service_config, out)
        assert (out / "docker/docker-compose.yml").exists()
        assert not (out / "docker/observability").exists()

    def test_spring_boot_version_in_gradle(self, tmp_path, generator):
        cfg = _config(build_tool=BuildTool.GRADLE_KOTLIN, spring_boot_version="4.0.3")
        out = tmp_path / "payment-service"
        generator.generate(cfg, out)
        content = (out / "build.gradle.kts").read_text()
        assert "4.0.3" in content

    def test_java25_in_pom(self, tmp_path, generator):
        cfg = _config(java_version=JavaVersion.V25)
        out = tmp_path / "payment-service"
        generator.generate(cfg, out)
        pom = (out / "pom.xml").read_text()
        assert "<java.version>25</java.version>" in pom

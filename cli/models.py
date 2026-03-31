from dataclasses import dataclass, field
from enum import Enum


class JavaVersion(str, Enum):
    V17 = "17"
    V21 = "21"


class TraceBackend(str, Enum):
    TEMPO = "tempo"
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    TEMPO_JAEGER = "tempo+jaeger"


class TargetEnvironment(str, Enum):
    DOCKER_COMPOSE = "docker-compose"
    KUBERNETES = "kubernetes"
    BOTH = "both"


class Database(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    H2 = "h2"
    NONE = "none"


class DeploymentMode(str, Enum):
    STANDALONE = "standalone"      # app + obs stack complet dans un seul compose
    MULTI_SERVICE = "multi-service"  # app seule, se connecte à un obs stack partagé


class MetricsBackend(str, Enum):
    PROMETHEUS = "prometheus"
    MIMIR = "mimir"


class BuildTool(str, Enum):
    MAVEN = "maven"
    GRADLE_KOTLIN = "gradle-kotlin"


class Extra(str, Enum):
    JWT = "jwt"
    KAFKA = "kafka"
    SECURITY = "security"


@dataclass
class ProjectConfig:
    service_name: str
    base_package: str
    java_version: JavaVersion
    trace_backend: TraceBackend
    environment: TargetEnvironment
    database: Database
    build_tool: BuildTool = BuildTool.MAVEN
    metrics_backend: MetricsBackend = MetricsBackend.PROMETHEUS
    deployment_mode: DeploymentMode = DeploymentMode.STANDALONE
    spring_boot_version: str = "4.0.3"
    demo: bool = False
    app_port: int = 8080

    # ------------------------------------------------------------------
    # Derived identifiers
    # ------------------------------------------------------------------

    @property
    def artifact_id(self) -> str:
        """Kebab-case, suitable for Maven artifactId and directory name."""
        return self.service_name.lower().replace("_", "-")

    @property
    def class_name(self) -> str:
        """PascalCase, suitable for Java class name prefix."""
        return "".join(part.capitalize() for part in self.artifact_id.split("-"))

    @property
    def package_path(self) -> str:
        """Base package as a filesystem path (dots → slashes)."""
        return self.base_package.replace(".", "/")

    # ------------------------------------------------------------------
    # Deployment mode helpers
    # ------------------------------------------------------------------

    @property
    def is_standalone(self) -> bool:
        return self.deployment_mode == DeploymentMode.STANDALONE

    @property
    def is_multi_service(self) -> bool:
        return self.deployment_mode == DeploymentMode.MULTI_SERVICE

    # ------------------------------------------------------------------
    # Metrics backend helpers
    # ------------------------------------------------------------------

    @property
    def use_prometheus(self) -> bool:
        return self.metrics_backend == MetricsBackend.PROMETHEUS

    @property
    def use_mimir(self) -> bool:
        return self.metrics_backend == MetricsBackend.MIMIR

    @property
    def metrics_remote_write_url(self) -> str:
        if self.use_mimir:
            return "http://mimir:9009/api/v1/push"
        return "http://prometheus:9090/api/v1/write"

    # ------------------------------------------------------------------
    # Build tool helpers
    # ------------------------------------------------------------------

    @property
    def use_maven(self) -> bool:
        return self.build_tool == BuildTool.MAVEN

    @property
    def use_gradle(self) -> bool:
        return self.build_tool == BuildTool.GRADLE_KOTLIN

    @property
    def use_gradle_kotlin(self) -> bool:
        return self.build_tool == BuildTool.GRADLE_KOTLIN

    @property
    def build_command(self) -> str:
        """Run command for the README."""
        if self.use_maven:
            return "./mvnw spring-boot:run"
        return "./gradlew bootRun"

    @property
    def wrapper_setup(self) -> str:
        """One-time wrapper generation command."""
        if self.use_maven:
            return "mvn wrapper:wrapper"
        return "gradle wrapper"

    # ------------------------------------------------------------------
    # Trace backend flags
    # ------------------------------------------------------------------

    @property
    def use_tempo(self) -> bool:
        return self.trace_backend in (TraceBackend.TEMPO, TraceBackend.TEMPO_JAEGER)

    @property
    def use_jaeger(self) -> bool:
        return self.trace_backend in (TraceBackend.JAEGER, TraceBackend.TEMPO_JAEGER)

    @property
    def use_zipkin(self) -> bool:
        return self.trace_backend == TraceBackend.ZIPKIN

    # ------------------------------------------------------------------
    # Environment flags
    # ------------------------------------------------------------------

    @property
    def use_docker(self) -> bool:
        return self.environment in (TargetEnvironment.DOCKER_COMPOSE, TargetEnvironment.BOTH)

    @property
    def use_kubernetes(self) -> bool:
        return self.environment in (TargetEnvironment.KUBERNETES, TargetEnvironment.BOTH)

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Factory for obs-only stack (used by create-stack)
    # ------------------------------------------------------------------

    @classmethod
    def for_obs_stack(
        cls,
        trace_backend: "TraceBackend",
        metrics_backend: "MetricsBackend",
    ) -> "ProjectConfig":
        """Minimal config for obs-only generation — only trace/metrics backend matter."""
        return cls(
            service_name="obs-stack",
            base_package="com.example",
            java_version=JavaVersion.V21,
            trace_backend=trace_backend,
            environment=TargetEnvironment.DOCKER_COMPOSE,
            database=Database.NONE,
            metrics_backend=metrics_backend,
            deployment_mode=DeploymentMode.MULTI_SERVICE,
        )

    @property
    def use_database(self) -> bool:
        return self.database != Database.NONE

    @property
    def datasource_url(self) -> str:
        """Spring Boot datasource URL with ${...} placeholders for env overrides."""
        db_name = self.artifact_id.replace("-", "_")
        match self.database:
            case Database.POSTGRESQL:
                return f"jdbc:postgresql://${{DB_HOST:localhost}}:${{DB_PORT:5432}}/${{DB_NAME:{db_name}}}"
            case Database.MYSQL:
                return f"jdbc:mysql://${{DB_HOST:localhost}}:${{DB_PORT:3306}}/${{DB_NAME:{db_name}}}?useSSL=false&serverTimezone=UTC"
            case Database.ORACLE:
                return f"jdbc:oracle:thin:@${{DB_HOST:localhost}}:${{DB_PORT:1521}}/${{DB_SERVICE:xe}}"
            case Database.H2:
                return f"jdbc:h2:mem:{db_name};MODE=PostgreSQL;DB_CLOSE_DELAY=-1"
            case _:
                return ""

    @property
    def db_default_user(self) -> str:
        match self.database:
            case Database.POSTGRESQL:
                return "postgres"
            case Database.MYSQL:
                return "root"
            case Database.ORACLE:
                return "system"
            case _:
                return "sa"

    @property
    def db_default_password(self) -> str:
        match self.database:
            case Database.H2:
                return ""
            case _:
                return "changeme"


@dataclass
class StackConfig:
    """Configuration for the create-stack command (shared obs + N services)."""

    stack_name: str
    trace_backend: TraceBackend
    metrics_backend: MetricsBackend
    services: list[ProjectConfig] = field(default_factory=list)

    @property
    def artifact_id(self) -> str:
        return self.stack_name.lower().replace("_", "-")

    @property
    def use_tempo(self) -> bool:
        return self.trace_backend in (TraceBackend.TEMPO, TraceBackend.TEMPO_JAEGER)

    @property
    def use_jaeger(self) -> bool:
        return self.trace_backend in (TraceBackend.JAEGER, TraceBackend.TEMPO_JAEGER)

    @property
    def use_zipkin(self) -> bool:
        return self.trace_backend == TraceBackend.ZIPKIN

    @property
    def use_prometheus(self) -> bool:
        return self.metrics_backend == MetricsBackend.PROMETHEUS

    @property
    def use_mimir(self) -> bool:
        return self.metrics_backend == MetricsBackend.MIMIR

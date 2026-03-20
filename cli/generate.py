from pathlib import Path

import click
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cli.generator import ProjectGenerator
from cli.models import (
    BuildTool,
    Database,
    Extra,
    JavaVersion,
    MetricsBackend,
    ProjectConfig,
    TargetEnvironment,
    TraceBackend,
)
from cli.validators import validate_package, validate_service_name

console = Console()


@click.group()
def main() -> None:
    """spring-obs-starter — Spring Boot 4 + OTel observability generator."""


@main.command()
@click.argument("service_name")
def create(service_name: str) -> None:
    """Generate a new Spring Boot 4 project with full OTel observability.

    SERVICE_NAME: name of the service (e.g. payment-service, order-api)
    """
    # --- Validate service name ---
    validation = validate_service_name(service_name)
    if validation is not True:
        console.print(f"[red]Error:[/red] {validation}")
        raise SystemExit(1)

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]spring-obs-starter[/bold cyan] — Spring Boot 4 + OTel",
            subtitle=f"Generating [bold]{service_name}[/bold]",
        )
    )
    console.print()

    # ------------------------------------------------------------------
    # Interactive questions
    # ------------------------------------------------------------------

    build_tool: BuildTool = questionary.select(
        "Build tool?",
        choices=[
            questionary.Choice("Maven (recommended)", BuildTool.MAVEN),
            questionary.Choice("Gradle — Kotlin DSL", BuildTool.GRADLE_KOTLIN),
            questionary.Choice("Gradle — Groovy DSL", BuildTool.GRADLE_GROOVY),
        ],
    ).ask()

    java_version: JavaVersion = questionary.select(
        "Java version?",
        choices=[
            questionary.Choice("21 LTS (recommended)", JavaVersion.V21),
            questionary.Choice("17 LTS", JavaVersion.V17),
        ],
    ).ask()

    trace_backend: TraceBackend = questionary.select(
        "Trace backend?",
        choices=[
            questionary.Choice("Tempo (recommended)", TraceBackend.TEMPO),
            questionary.Choice("Jaeger", TraceBackend.JAEGER),
            questionary.Choice("Zipkin", TraceBackend.ZIPKIN),
            questionary.Choice("Tempo + Jaeger", TraceBackend.TEMPO_JAEGER),
        ],
    ).ask()

    metrics_backend: MetricsBackend = questionary.select(
        "Metrics backend?",
        choices=[
            questionary.Choice("Prometheus (recommended)", MetricsBackend.PROMETHEUS),
            questionary.Choice("Mimir (long-term storage, Prometheus-compatible)", MetricsBackend.MIMIR),
        ],
    ).ask()

    environment: TargetEnvironment = questionary.select(
        "Target environment?",
        choices=[
            questionary.Choice("Docker Compose (local dev)", TargetEnvironment.DOCKER_COMPOSE),
            questionary.Choice("Kubernetes / K3s", TargetEnvironment.KUBERNETES),
            questionary.Choice("Both", TargetEnvironment.BOTH),
        ],
    ).ask()

    database: Database = questionary.select(
        "Database?",
        choices=[
            questionary.Choice("None (in-memory / no persistence)", Database.NONE),
            questionary.Choice("PostgreSQL", Database.POSTGRESQL),
            questionary.Choice("MySQL", Database.MYSQL),
            questionary.Choice("Oracle", Database.ORACLE),
            questionary.Choice("H2 (dev only)", Database.H2),
        ],
    ).ask()

    default_pkg = f"com.example.{service_name.lower().replace('-', '').replace('_', '')}"
    base_package: str = questionary.text(
        "Base package?",
        default=default_pkg,
        validate=validate_package,
    ).ask()

    # ------------------------------------------------------------------
    # Build config
    # ------------------------------------------------------------------

    config = ProjectConfig(
        service_name=service_name,
        base_package=base_package,
        java_version=java_version,
        trace_backend=trace_backend,
        environment=environment,
        database=database,
        build_tool=build_tool,
        metrics_backend=metrics_backend,
    )

    output_dir = Path.cwd() / config.artifact_id

    if output_dir.exists():
        overwrite = questionary.confirm(
            f"Directory '{config.artifact_id}' already exists. Overwrite?",
            default=False,
        ).ask()
        if not overwrite:
            console.print("[yellow]Aborted.[/yellow]")
            raise SystemExit(0)

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    generator = ProjectGenerator()

    steps = [
        f"Generating Spring Boot {config.spring_boot_version} project...",
        "Configuring OpenTelemetry native starter...",
        "Setting up OTel Collector pipelines (traces / metrics / logs)...",
        "Wiring Logback OTel Appender for log correlation...",
    ]
    if config.use_docker:
        steps += [
            "Generating Docker Compose stack with health checks...",
            "Provisioning Grafana dashboards (JVM, HTTP, Logs-Traces)...",
        ]
    steps.append("Writing README with quick start guide...")

    console.print()
    for step in steps:
        with console.status(f"[cyan]{step}[/cyan]"):
            pass  # actual generation happens in one call below
        console.print(f"  [green]✔[/green] {step}")

    generator.generate(config, output_dir)

    # ------------------------------------------------------------------
    # Success output
    # ------------------------------------------------------------------

    console.print()
    console.rule(style="green")

    result = Text()
    result.append(f"\n  ✅ Project ready: ./{config.artifact_id}\n", style="bold green")
    console.print(result)

    console.rule(style="green")
    console.print()

    console.print("  [bold]Quick start:[/bold]")
    console.print(f"  $ cd {config.artifact_id}")
    if config.use_docker:
        console.print("  $ docker compose -f docker/docker-compose.yml up -d")
    console.print("  $ ./mvnw spring-boot:run")
    console.print()

    if config.use_docker:
        console.print("  [bold]Endpoints:[/bold]")
        console.print("  Grafana    → [link]http://localhost:3000[/link]  (admin / admin)")
        console.print("  Prometheus → [link]http://localhost:9090[/link]")
        if config.use_tempo:
            console.print("  Tempo      → [link]http://localhost:3200[/link]")
        if config.use_jaeger:
            console.print("  Jaeger     → [link]http://localhost:16686[/link]")
        if config.use_zipkin:
            console.print("  Zipkin     → [link]http://localhost:9411[/link]")
        console.print(f"  App        → [link]http://localhost:8080/actuator/health[/link]")
        console.print()

    console.print(
        "  [dim]⚠  Change Grafana credentials before going to production.[/dim]"
    )
    console.print()

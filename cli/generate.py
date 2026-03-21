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
    DeploymentMode,
    Extra,
    JavaVersion,
    MetricsBackend,
    ProjectConfig,
    TargetEnvironment,
    TraceBackend,
)
from cli.detector import (
    detect_base_package,
    detect_build_tool,
    detect_database,
    detect_java_version,
    detect_service_name,
    detect_spring_boot_version,
    discover_projects,
    has_dependency,
    has_otel_in_yml,
)
from cli.patcher import patch_application_yml, patch_build_file
from cli.validators import validate_package, validate_service_name, validate_output_dir

console = Console()


_BANNER = """
[bold cyan]┌─────────────────────────────────────────────────────────────────┐[/bold cyan]
[bold cyan]│[/bold cyan]                                                                 [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold white] ___  ___  ___         [green]█▀█ █▄▄ █▀[/green]                         [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold white]/ __|| _ )||_ )  [cyan]───[/cyan]  [green]█▄█ █▄█ ▄█[/green]  [bold white]Spring Boot 4 + OTel[/bold white]   [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold white]\__ \| _ \ / /         [green]Observability Starter[/green]              [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold white]|___/|___//___|                                            [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]                                                                 [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [dim]Traces · Metrics · Logs — correlated out of the box[/dim]         [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]                                                                 [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold]Author :[/bold] [cyan]amaryange[/cyan]           [bold]Web :[/bold] [link=https://amarycode.dev]amarycode.dev[/link]          [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]                                                                 [bold cyan]│[/bold cyan]
[bold cyan]└─────────────────────────────────────────────────────────────────┘[/bold cyan]
"""


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """spring-obs-starter — Spring Boot 4 + OTel observability generator."""
    if ctx.invoked_subcommand is None:
        console.print(_BANNER)
        console.print("  [bold]Commands:[/bold]")
        console.print("  [cyan]sbo create[/cyan] <service-name>   Generate a new project")
        console.print("  [cyan]sbo init-obs[/cyan]                Generate shared obs stack")
        console.print("  [cyan]sbo add[/cyan] [PATH...]           Add OTel to existing project(s)")
        console.print()
        console.print("  Run [cyan]sbo <command> --help[/cyan] for details.")
        console.print()
    else:
        console.print(_BANNER)


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

    deployment_mode: DeploymentMode = questionary.select(
        "Deployment mode?",
        choices=[
            questionary.Choice(
                "Standalone  — app + obs stack complet (dev solo)",
                DeploymentMode.STANDALONE,
            ),
            questionary.Choice(
                "Multi-service — app seule, obs stack partagé (sbo init-obs)",
                DeploymentMode.MULTI_SERVICE,
            ),
        ],
    ).ask()

    metrics_backend: MetricsBackend = MetricsBackend.PROMETHEUS
    if deployment_mode == DeploymentMode.STANDALONE:
        metrics_backend = questionary.select(
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
        deployment_mode=deployment_mode,
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
        "Wiring Logback OTel Appender for log correlation...",
    ]
    if config.use_docker:
        if config.is_standalone:
            steps += [
                "Setting up OTel Collector pipelines (traces / metrics / logs)...",
                "Generating Docker Compose stack with health checks...",
                "Provisioning Grafana dashboards (JVM, HTTP, Logs-Traces)...",
            ]
        else:
            steps.append("Generating Docker Compose service config (obs-network)...")
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


@main.command("init-obs")
def init_obs() -> None:
    """Generate a shared observability stack for multi-service setups.

    Creates a standalone obs-stack/ directory with OTel Collector, metrics backend,
    Loki, optional Tempo/Jaeger, and Grafana — all connected via obs-network.

    Services generated with --deployment-mode multi-service connect to this stack.
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]spring-obs-starter[/bold cyan] — Shared Observability Stack",
            subtitle="OTel Collector · Metrics · Loki · Grafana",
        )
    )
    console.print()

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

    output_name: str = questionary.text(
        "Output directory?",
        default="obs-stack",
        validate=validate_output_dir,
    ).ask()

    output_dir = Path.cwd() / output_name

    if output_dir.exists():
        overwrite = questionary.confirm(
            f"Directory '{output_name}' already exists. Overwrite?",
            default=False,
        ).ask()
        if not overwrite:
            console.print("[yellow]Aborted.[/yellow]")
            raise SystemExit(0)

    config = ProjectConfig.for_obs_stack(
        trace_backend=trace_backend,
        metrics_backend=metrics_backend,
    )

    generator = ProjectGenerator()

    steps = [
        "Generating OTel Collector config (traces / metrics / logs pipelines)...",
        f"Configuring {'Prometheus' if config.use_prometheus else 'Mimir'} metrics backend...",
        "Configuring Loki log backend...",
    ]
    if config.use_tempo:
        steps.append("Configuring Tempo trace backend with span metrics...")
    if config.use_jaeger:
        steps.append("Configuring Jaeger trace backend...")
    if config.use_zipkin:
        steps.append("Configuring Zipkin trace backend...")
    steps += [
        "Provisioning Grafana dashboards (JVM, HTTP, Logs-Traces)...",
        "Writing Docker Compose stack with obs-network...",
    ]

    console.print()
    for step in steps:
        with console.status(f"[cyan]{step}[/cyan]"):
            pass
        console.print(f"  [green]✔[/green] {step}")

    generator.generate_obs_stack(config, output_dir)

    console.print()
    console.rule(style="green")

    result = Text()
    result.append(f"\n  ✅ Obs stack ready: ./{output_name}\n", style="bold green")
    console.print(result)

    console.rule(style="green")
    console.print()

    console.print("  [bold]Quick start:[/bold]")
    console.print(f"  $ cd {output_name}")
    console.print("  $ docker compose up -d")
    console.print()

    console.print("  [bold]Endpoints:[/bold]")
    console.print("  Grafana    → [link]http://localhost:3000[/link]  (admin / admin)")
    if config.use_prometheus:
        console.print("  Prometheus → [link]http://localhost:9090[/link]")
    else:
        console.print("  Mimir      → [link]http://localhost:9009[/link]")
    if config.use_tempo:
        console.print("  Tempo      → [link]http://localhost:3200[/link]")
    if config.use_jaeger:
        console.print("  Jaeger     → [link]http://localhost:16686[/link]")
    if config.use_zipkin:
        console.print("  Zipkin     → [link]http://localhost:9411[/link]")
    console.print("  OTel Col.  → [link]http://localhost:4318[/link]  (OTLP HTTP)")
    console.print()

    console.print("  [bold]Connect a service:[/bold]")
    console.print("  $ sbo create my-service  [dim]# choose Multi-service mode[/dim]")
    console.print()

    console.print(
        "  [dim]⚠  Change Grafana credentials before going to production.[/dim]"
    )
    console.print()


@main.command("add")
@click.argument("project_paths", nargs=-1, metavar="PATH...")
def add(project_paths: tuple[str, ...]) -> None:
    """Add OTel observability wiring to one or more existing Spring Boot 4 projects.

    PATH: one or more project roots (default: current directory)

    Non-destructive: skips files that already exist or are already configured.

    Examples:
      sbo add .
      sbo add service-a/ service-b/ service-c/
    """
    raw_paths = [Path(p).resolve() for p in project_paths] if project_paths else [Path.cwd()]

    # Expand monorepo directories: if a path has no build file but contains
    # Spring Boot subdirectories, auto-discover them (depth 1).
    resolved: list[Path] = []
    for p in raw_paths:
        if detect_build_tool(p) is not None:
            resolved.append(p)
        else:
            discovered = discover_projects(p)
            if discovered:
                console.print(f"\n  [bold]Monorepo detected:[/bold] {p.name}/")
                for d in discovered:
                    console.print(f"  [cyan]→[/cyan] {d.relative_to(p)}")
                console.print()
                if not questionary.confirm(f"Process {len(discovered)} service(s)?", default=True).ask():
                    continue
                resolved.extend(discovered)
            else:
                console.print(f"[yellow]Warning:[/yellow] No Spring Boot project found in {p} — skipped.")

    if not resolved:
        console.print("[red]No projects to process.[/red]")
        raise SystemExit(1)

    for idx, path in enumerate(resolved):
        if len(resolved) > 1:
            console.rule(f"[cyan]{idx + 1}/{len(resolved)} — {path.name}[/cyan]")
        _add_single(path)


def _add_single(path: Path) -> None:
    """Core logic for adding observability to a single project."""

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]spring-obs-starter[/bold cyan] — Add Observability",
            subtitle=f"[bold]{path.name}[/bold]",
        )
    )
    console.print()

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    build_tool = detect_build_tool(path)
    if build_tool is None:
        console.print("[red]Error:[/red] No pom.xml or build.gradle found. Is this a Spring Boot project?")
        return

    if not (path / "src" / "main" / "java").exists():
        console.print("[red]Error:[/red] No src/main/java directory found.")
        return

    service_name = detect_service_name(path, build_tool)
    java_version = detect_java_version(path, build_tool)
    base_package = detect_base_package(path)
    sb_version = detect_spring_boot_version(path, build_tool)

    console.print("  [bold]Detected project:[/bold]")
    console.print(f"  Build tool    : {build_tool.value}")
    console.print(f"  Service name  : {service_name}")
    console.print(f"  Java version  : {java_version.value}")
    console.print(f"  Base package  : {base_package or '[yellow]not found[/yellow]'}")
    console.print(f"  Spring Boot   : {sb_version or '[yellow]not found[/yellow]'}")
    console.print()

    if sb_version and not sb_version.startswith("4."):
        console.print(f"[yellow]Warning:[/yellow] Detected Spring Boot {sb_version}. "
                      "This tool targets Spring Boot 4.x — some configurations may not apply.")
        if not questionary.confirm("Continue anyway?", default=False).ask():
            return
        console.print()

    if base_package is None:
        base_package = questionary.text(
            "Could not auto-detect base package. Enter it manually:",
            validate=validate_package,
        ).ask()
        console.print()

    # ------------------------------------------------------------------
    # What will be done
    # ------------------------------------------------------------------

    otel_already = has_dependency(path, build_tool, "spring-boot-starter-opentelemetry")
    yml_already = has_otel_in_yml(path)
    installer_path = (
        path / "src" / "main" / "java"
        / base_package.replace(".", "/")
        / "config"
        / "OtelLogbackInstaller.java"
    )
    logback_path = path / "src" / "main" / "resources" / "logback-spring.xml"

    console.print("  [bold]Planned changes:[/bold]")
    console.print(f"  {'[dim]skip[/dim]  ' if otel_already else '[green]add[/green]   '}  OTel dependencies in build file")
    console.print(f"  {'[dim]skip[/dim]  ' if yml_already else '[green]patch[/green] '}  application.yml (OTel properties)")
    console.print(f"  {'[dim]skip[/dim]  ' if installer_path.exists() else '[green]create[/green]'}  {installer_path.relative_to(path)}")
    console.print(f"  {'[dim]skip[/dim]  ' if logback_path.exists() else '[green]create[/green]'}  src/main/resources/logback-spring.xml")
    console.print()

    if not questionary.confirm("Apply changes?", default=True).ask():
        console.print("[yellow]Skipped.[/yellow]")
        return

    # ------------------------------------------------------------------
    # Build minimal ProjectConfig for template rendering
    # ------------------------------------------------------------------

    config = ProjectConfig(
        service_name=service_name,
        base_package=base_package,
        java_version=java_version,
        trace_backend=TraceBackend.TEMPO,  # not used in these specific templates
        environment=TargetEnvironment.DOCKER_COMPOSE,
        database=Database.NONE,
        build_tool=build_tool,
    )

    # ------------------------------------------------------------------
    # Apply changes
    # ------------------------------------------------------------------

    generator = ProjectGenerator()
    done: list[str] = []
    skipped: list[str] = []

    # 1. Build file
    added_deps = patch_build_file(path, build_tool)
    if added_deps:
        done.append(f"Added deps: {', '.join(added_deps)}")
    else:
        skipped.append("OTel dependencies (already present)")

    # 2. application.yml / application.yaml — prefer the existing file
    resources_dir = path / "src" / "main" / "resources"
    yml_path = resources_dir / "application.yml"
    yaml_path = resources_dir / "application.yaml"
    if yaml_path.exists() and not yml_path.exists():
        yml_path = yaml_path
    result = patch_application_yml(yml_path)
    if result == "patched":
        done.append("application.yml (OTel block appended)")
    elif result == "created":
        done.append("application.yml (created with OTel config)")
    else:
        skipped.append("application.yml (OTel already configured)")

    # 3. OtelLogbackInstaller.java
    if not installer_path.exists():
        installer_path.parent.mkdir(parents=True, exist_ok=True)
        template = generator.env.get_template("spring-boot/4.0/OtelLogbackInstaller.java.j2")
        installer_path.write_text(template.render(config=config), encoding="utf-8")
        done.append(str(installer_path.relative_to(path)))
    else:
        skipped.append("OtelLogbackInstaller.java (already exists)")

    # 4. logback-spring.xml
    if not logback_path.exists():
        generator._copy("spring-boot/4.0/logback-spring.xml", logback_path)
        done.append("src/main/resources/logback-spring.xml")
    else:
        skipped.append("logback-spring.xml (already exists)")

    # ------------------------------------------------------------------
    # Docker Compose (optional)
    # ------------------------------------------------------------------

    compose_path = path / "docker" / "docker-compose.yml"
    if not compose_path.exists():
        console.print()
        want_docker = questionary.confirm(
            "Generate Docker Compose to connect to the shared obs stack (obs-network)?",
            default=True,
        ).ask()

        if want_docker:
            database = detect_database(path, build_tool)
            deployment_mode = questionary.select(
                "Deployment mode?",
                choices=[
                    questionary.Choice(
                        "Multi-service — connects to shared obs-network (sbo init-obs)",
                        DeploymentMode.MULTI_SERVICE,
                    ),
                    questionary.Choice(
                        "Standalone — embed full obs stack in this project",
                        DeploymentMode.STANDALONE,
                    ),
                ],
            ).ask()

            config = ProjectConfig(
                service_name=service_name,
                base_package=base_package,
                java_version=java_version,
                trace_backend=TraceBackend.TEMPO,
                environment=TargetEnvironment.DOCKER_COMPOSE,
                database=database,
                build_tool=build_tool,
                deployment_mode=deployment_mode,
            )

            if deployment_mode == DeploymentMode.MULTI_SERVICE:
                compose_path.parent.mkdir(parents=True, exist_ok=True)
                template = generator.env.get_template("docker/docker-compose.service.yml.j2")
                compose_path.write_text(template.render(config=config), encoding="utf-8")
                done.append("docker/docker-compose.yml (multi-service → obs-network)")
            else:
                # Standalone: full obs stack
                trace_backend = questionary.select(
                    "Trace backend?",
                    choices=[
                        questionary.Choice("Tempo (recommended)", TraceBackend.TEMPO),
                        questionary.Choice("Jaeger", TraceBackend.JAEGER),
                        questionary.Choice("Zipkin", TraceBackend.ZIPKIN),
                        questionary.Choice("Tempo + Jaeger", TraceBackend.TEMPO_JAEGER),
                    ],
                ).ask()
                metrics_backend = questionary.select(
                    "Metrics backend?",
                    choices=[
                        questionary.Choice("Prometheus (recommended)", MetricsBackend.PROMETHEUS),
                        questionary.Choice("Mimir", MetricsBackend.MIMIR),
                    ],
                ).ask()
                config = ProjectConfig(
                    service_name=service_name,
                    base_package=base_package,
                    java_version=java_version,
                    trace_backend=trace_backend,
                    environment=TargetEnvironment.DOCKER_COMPOSE,
                    database=database,
                    build_tool=build_tool,
                    metrics_backend=metrics_backend,
                    deployment_mode=DeploymentMode.STANDALONE,
                )
                docker_out = path / "docker"
                for tpl, out in generator._standalone_docker_files(config):
                    full = docker_out / out.removeprefix("docker/")
                    full.parent.mkdir(parents=True, exist_ok=True)
                    if tpl.endswith(".j2"):
                        generator._render(config, tpl, full)
                    else:
                        generator._copy(tpl, full)
                done.append("docker/ (standalone obs stack)")
    else:
        skipped.append("docker/docker-compose.yml (already exists)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    console.print()
    console.rule(style="green")
    console.print()

    if done:
        console.print("  [bold green]Applied:[/bold green]")
        for item in done:
            console.print(f"  [green]✔[/green] {item}")
    if skipped:
        console.print("  [bold dim]Skipped:[/bold dim]")
        for item in skipped:
            console.print(f"  [dim]–[/dim] {item}")

    console.print()
    console.print(
        "  [dim]⚠  If management: already existed in application.yml, "
        "merge the appended block manually.[/dim]"
    )
    console.print(
        "  [dim]ℹ  Run sbo init-obs to generate the shared observability stack.[/dim]"
    )
    console.print()

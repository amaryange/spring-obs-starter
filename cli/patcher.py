"""
Non-destructive patching utilities for sbo add.
Each function returns a description of what was done (or skipped).
"""
from pathlib import Path

from cli.models import BuildTool

# ---------------------------------------------------------------------------
# Dependency descriptors
# ---------------------------------------------------------------------------

OTEL_DEPS_MAVEN = [
    {"groupId": "org.springframework.boot", "artifactId": "spring-boot-starter-opentelemetry"},
    {"groupId": "org.springframework.boot", "artifactId": "spring-boot-starter-aspectj"},
    {
        "groupId": "io.opentelemetry.instrumentation",
        "artifactId": "opentelemetry-logback-appender-1.0",
        "version": "2.21.0-alpha",
    },
]

OTEL_DEPS_GRADLE_KOTLIN = [
    'implementation("org.springframework.boot:spring-boot-starter-opentelemetry")',
    'implementation("org.springframework.boot:spring-boot-starter-aspectj")',
    'implementation("io.opentelemetry.instrumentation:opentelemetry-logback-appender-1.0:2.21.0-alpha")',
]

# ---------------------------------------------------------------------------
# Maven pom.xml
# ---------------------------------------------------------------------------

def patch_pom_xml(pom_path: Path) -> list[str]:
    """Add missing OTel dependencies. Returns list of added artifactIds."""
    content = pom_path.read_text(encoding="utf-8")
    added: list[str] = []

    for dep in OTEL_DEPS_MAVEN:
        if dep["artifactId"] in content:
            continue
        lines = [
            "        <dependency>",
            f"            <groupId>{dep['groupId']}</groupId>",
            f"            <artifactId>{dep['artifactId']}</artifactId>",
        ]
        if "version" in dep:
            lines.append(f"            <version>{dep['version']}</version>")
        lines.append("        </dependency>")
        snippet = "\n".join(lines) + "\n"

        # rfind: the LAST </dependencies> is the main block (after dependencyManagement)
        idx = content.rfind("    </dependencies>")
        if idx == -1:
            continue
        content = content[:idx] + snippet + content[idx:]
        added.append(dep["artifactId"])

    if added:
        pom_path.write_text(content, encoding="utf-8")
    return added


# ---------------------------------------------------------------------------
# Gradle
# ---------------------------------------------------------------------------

def _insert_into_dependencies_block(content: str, snippet: str) -> str:
    """Insert snippet before the closing } of the dependencies { ... } block."""
    lines = content.splitlines(keepends=True)
    depth = 0
    in_deps = False
    insert_at = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_deps and stripped.startswith("dependencies") and "{" in stripped:
            in_deps = True
            depth = stripped.count("{") - stripped.count("}")
            continue
        if in_deps:
            depth += stripped.count("{") - stripped.count("}")
            if depth <= 0:
                insert_at = i
                break

    if insert_at == -1:
        # Fallback: just append to end of file
        return content + "\ndependencies {\n" + snippet + "\n}\n"

    lines.insert(insert_at, snippet + "\n")
    return "".join(lines)


def patch_gradle_kotlin(build_path: Path) -> list[str]:
    content = build_path.read_text(encoding="utf-8")
    added: list[str] = []

    for dep in OTEL_DEPS_GRADLE_KOTLIN:
        artifact = dep.split(":")[1].strip('"')
        if artifact in content:
            continue
        content = _insert_into_dependencies_block(content, f"    {dep}")
        added.append(artifact)

    if added:
        build_path.write_text(content, encoding="utf-8")
    return added



def patch_build_file(project_path: Path, build_tool: BuildTool) -> list[str]:
    if build_tool == BuildTool.MAVEN:
        return patch_pom_xml(project_path / "pom.xml")
    else:
        return patch_gradle_kotlin(project_path / "build.gradle.kts")


# ---------------------------------------------------------------------------
# application.yml
# ---------------------------------------------------------------------------

_OTEL_YML_BLOCK = """\

# --- OpenTelemetry (added by sbo add) ---
# ⚠  If a 'management:' key already exists above, merge these nested keys into it.
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus, metrics
  metrics:
    tags:
      application: ${spring.application.name}
    distribution:
      percentiles-histogram:
        http:
          server:
            requests: true
  tracing:
    sampling:
      probability: ${OTEL_SAMPLING_PROBABILITY:1.0}
  otlp:
    metrics:
      export:
        url: ${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318}/v1/metrics
  opentelemetry:
    tracing:
      export:
        otlp:
          endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318}/v1/traces
    logging:
      export:
        otlp:
          endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318}/v1/logs
"""


def patch_application_yml(yml_path: Path) -> str:
    """
    Appends OTel configuration to application.yml.
    Returns 'patched', 'skipped' (already configured), or 'created'.
    """
    if yml_path.exists():
        content = yml_path.read_text(encoding="utf-8")
        if "otlp" in content.lower() or "opentelemetry" in content.lower():
            return "skipped"
        yml_path.write_text(content.rstrip("\n") + _OTEL_YML_BLOCK, encoding="utf-8")
        return "patched"
    else:
        yml_path.parent.mkdir(parents=True, exist_ok=True)
        yml_path.write_text(_OTEL_YML_BLOCK.lstrip("\n"), encoding="utf-8")
        return "created"

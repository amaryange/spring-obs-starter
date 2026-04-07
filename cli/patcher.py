"""
Non-destructive patching utilities for sos add.
Each function returns a description of what was done (or skipped).
"""
import re
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

    # Detect indentation from existing <dependency> blocks (2 or 4 spaces, or tabs)
    indent_m = re.search(r"^(\s+)<dependency>", content, re.MULTILINE)
    dep_indent = indent_m.group(1) if indent_m else "        "
    inner_indent = dep_indent + "    "

    for dep in OTEL_DEPS_MAVEN:
        if dep["artifactId"] in content:
            continue
        lines = [
            f"{dep_indent}<dependency>",
            f"{inner_indent}<groupId>{dep['groupId']}</groupId>",
            f"{inner_indent}<artifactId>{dep['artifactId']}</artifactId>",
        ]
        if "version" in dep:
            lines.append(f"{inner_indent}<version>{dep['version']}</version>")
        lines.append(f"{dep_indent}</dependency>")
        snippet = "\n".join(lines) + "\n"

        # Find the LAST </dependencies> closing tag (main block, after dependencyManagement)
        m = None
        for m in re.finditer(r"^\s*</dependencies>", content, re.MULTILINE):
            pass
        if m is None:
            continue
        content = content[:m.start()] + snippet + content[m.start():]
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
        m = re.search(r":([a-zA-Z0-9\-._]+)", dep)
        artifact = m.group(1) if m else dep
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

# OTel properties nested under management:
_OTEL_MANAGEMENT_NESTED = """\
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

_OTEL_YML_BLOCK = "\n# --- OpenTelemetry (added by sos add) ---\nmanagement:\n" + _OTEL_MANAGEMENT_NESTED


def patch_application_yml(yml_path: Path) -> str:
    """
    Appends OTel configuration to application.yml.
    If a top-level 'management:' key already exists, merges nested keys into it.
    Returns 'patched', 'skipped' (already configured), or 'created'.
    """
    if yml_path.exists():
        content = yml_path.read_text(encoding="utf-8")
        if "otlp" in content.lower() or "opentelemetry" in content.lower():
            return "skipped"

        # Check if a top-level management: key already exists
        if re.search(r"^management\s*:", content, re.MULTILINE):
            # Find the end of the management: block (next top-level key or EOF)
            m = re.search(r"^management\s*:.*?(?=\n\S|\Z)", content, re.MULTILINE | re.DOTALL)
            if m:
                insert_pos = m.end()
                nested = "\n# --- OpenTelemetry (added by sos add) ---\n" + _OTEL_MANAGEMENT_NESTED
                content = content[:insert_pos] + nested + content[insert_pos:]
                yml_path.write_text(content, encoding="utf-8")
                return "patched"

        yml_path.write_text(content.rstrip("\n") + _OTEL_YML_BLOCK, encoding="utf-8")
        return "patched"
    else:
        yml_path.parent.mkdir(parents=True, exist_ok=True)
        yml_path.write_text(_OTEL_YML_BLOCK.lstrip("\n"), encoding="utf-8")
        return "created"

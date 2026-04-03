"""
Project detection utilities for sos add.
All functions are pure (read-only) and return None / sensible defaults on failure.
"""
import re
from pathlib import Path

from cli.models import BuildTool, JavaVersion


def detect_build_tool(project_path: Path) -> BuildTool | None:
    if (project_path / "pom.xml").exists():
        return BuildTool.MAVEN
    if (project_path / "build.gradle.kts").exists():
        return BuildTool.GRADLE_KOTLIN
    return None


def detect_service_name(project_path: Path, build_tool: BuildTool) -> str:
    """Returns the project artifact/module name, fallback to directory name."""
    try:
        if build_tool == BuildTool.MAVEN:
            content = (project_path / "pom.xml").read_text(encoding="utf-8")
            # Remove <parent> block to avoid matching parent's artifactId
            content_no_parent = re.sub(r"<parent>.*?</parent>", "", content, flags=re.DOTALL)
            m = re.search(r"<artifactId>([^<]+)</artifactId>", content_no_parent)
            if m:
                return m.group(1).strip()
        elif build_tool == BuildTool.GRADLE_KOTLIN:
            settings = project_path / "settings.gradle.kts"
            if settings.exists():
                m = re.search(r'rootProject\.name\s*=\s*"([^"]+)"', settings.read_text(encoding="utf-8"))
                if m:
                    return m.group(1)
    except OSError:
        pass
    return project_path.name


def detect_java_version(project_path: Path, build_tool: BuildTool) -> JavaVersion:
    try:
        if build_tool == BuildTool.MAVEN:
            content = (project_path / "pom.xml").read_text(encoding="utf-8")
            for pattern in [r"<java\.version>(\d+)", r"<maven\.compiler\.source>(\d+)"]:
                m = re.search(pattern, content)
                if m:
                    return JavaVersion.V17 if m.group(1) == "17" else JavaVersion.V21
        else:
            fname = "build.gradle.kts"
            content = (project_path / fname).read_text(encoding="utf-8")
            for pattern in [r"VERSION_(\d+)", r"sourceCompatibility\s*=\s*[\"']?(\d+)"]:
                m = re.search(pattern, content)
                if m:
                    return JavaVersion.V17 if m.group(1) == "17" else JavaVersion.V21
    except OSError:
        pass
    return JavaVersion.V21


def detect_spring_boot_version(project_path: Path, build_tool: BuildTool) -> str | None:
    try:
        if build_tool == BuildTool.MAVEN:
            content = (project_path / "pom.xml").read_text(encoding="utf-8")
            # Look for spring-boot-starter-parent version
            m = re.search(
                r"<artifactId>spring-boot-starter-parent</artifactId>\s*<version>([^<]+)</version>",
                content,
            )
            if m:
                return m.group(1).strip()
        else:
            fname = "build.gradle.kts"
            content = (project_path / fname).read_text(encoding="utf-8")
            m = re.search(r'id\s*\(\s*"org\.springframework\.boot"\s*\)\s*version\s*"([^"]+)"', content)
            if not m:
                m = re.search(r"org\.springframework\.boot.*?version\s+['\"]([^'\"]+)['\"]", content)
            if m:
                return m.group(1).strip()
    except OSError:
        pass
    return None


def detect_base_package(project_path: Path) -> str | None:
    """Finds the package of the @SpringBootApplication class."""
    java_root = project_path / "src" / "main" / "java"
    if not java_root.exists():
        return None
    for java_file in java_root.rglob("*.java"):
        try:
            content = java_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if "@SpringBootApplication" in content:
            m = re.search(r"^package\s+([\w.]+);", content, re.MULTILINE)
            if m:
                return m.group(1)
    return None


def has_dependency(project_path: Path, build_tool: BuildTool, artifact_id: str) -> bool:
    try:
        if build_tool == BuildTool.MAVEN:
            return artifact_id in (project_path / "pom.xml").read_text(encoding="utf-8")
        fname = "build.gradle.kts"
        return artifact_id in (project_path / fname).read_text(encoding="utf-8")
    except OSError:
        return False


def detect_database(project_path: Path, build_tool: BuildTool) -> "Database":
    """Infer database from driver/dialect dependencies in the build file."""
    from cli.models import Database
    try:
        if build_tool == BuildTool.MAVEN:
            content = (project_path / "pom.xml").read_text(encoding="utf-8")
        else:
            fname = "build.gradle.kts"
            content = (project_path / fname).read_text(encoding="utf-8")
    except OSError:
        return Database.NONE

    if "postgresql" in content:
        return Database.POSTGRESQL
    if "mysql-connector" in content or "mysql:" in content:
        return Database.MYSQL
    if "ojdbc" in content or "oracle" in content.lower():
        return Database.ORACLE
    if "com.h2database" in content or ":h2" in content:
        return Database.H2
    return Database.NONE


def discover_projects(directory: Path) -> list[Path]:
    """
    Return all immediate subdirectories that look like Spring Boot projects.
    Used for monorepo layouts: sos add services/ discovers services/*/pom.xml.
    """
    found: list[Path] = []
    try:
        for child in sorted(directory.iterdir()):
            if child.is_dir() and detect_build_tool(child) is not None:
                found.append(child)
    except OSError:
        pass
    return found


def has_otel_in_yml(project_path: Path) -> bool:
    """Returns True if application.yml or application.yaml already has OTel/OTLP configuration."""
    resources = project_path / "src" / "main" / "resources"
    for name in ("application.yml", "application.yaml"):
        yml = resources / name
        if yml.exists():
            content = yml.read_text(encoding="utf-8").lower()
            if "management.otlp" in content or "opentelemetry" in content or "otlp" in content:
                return True
    return False

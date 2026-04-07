"""Tests for sos add — detector.py and patcher.py."""
import pytest
from pathlib import Path

from cli.detector import (
    detect_base_package,
    detect_build_tool,
    detect_database,
    detect_java_version,
    detect_service_name,
    detect_spring_boot_version,
    has_dependency,
    has_otel_in_yml,
)
from cli.models import BuildTool, Database, JavaVersion
from cli.patcher import patch_application_yml, patch_build_file, patch_pom_xml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pom(tmp_path: Path, java_version: str = "21", sb_version: str = "4.0.5",
              indent: str = "    ", extra_deps: str = "") -> Path:
    pom = tmp_path / "pom.xml"
    pom.write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<project>
{indent}<parent>
{indent}{indent}<groupId>org.springframework.boot</groupId>
{indent}{indent}<artifactId>spring-boot-starter-parent</artifactId>
{indent}{indent}<version>{sb_version}</version>
{indent}</parent>
{indent}<artifactId>my-service</artifactId>
{indent}<properties>
{indent}{indent}<java.version>{java_version}</java.version>
{indent}</properties>
{indent}<dependencies>
{extra_deps}
{indent}</dependencies>
</project>
""", encoding="utf-8")
    return pom


def _make_gradle(tmp_path: Path, java_version: str = "21") -> Path:
    build = tmp_path / "build.gradle.kts"
    settings = tmp_path / "settings.gradle.kts"
    settings.write_text('rootProject.name = "my-service"\n')
    build.write_text(f"""\
plugins {{
    java
    id("org.springframework.boot") version "4.0.5"
}}
java {{
    sourceCompatibility = JavaVersion.VERSION_{java_version}
    targetCompatibility = JavaVersion.VERSION_{java_version}
}}
dependencies {{
    implementation("org.springframework.boot:spring-boot-starter-web")
}}
""", encoding="utf-8")
    return build


def _make_spring_app(tmp_path: Path, package: str = "com.example.payment") -> None:
    pkg_path = tmp_path / "src" / "main" / "java" / package.replace(".", "/")
    pkg_path.mkdir(parents=True)
    (pkg_path / "PaymentApplication.java").write_text(
        f"package {package};\n\n@SpringBootApplication\npublic class PaymentApplication {{}}\n"
    )


# ---------------------------------------------------------------------------
# detector — detect_build_tool
# ---------------------------------------------------------------------------

class TestDetectBuildTool:
    def test_detects_maven(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        assert detect_build_tool(tmp_path) == BuildTool.MAVEN

    def test_detects_gradle_kotlin(self, tmp_path):
        (tmp_path / "build.gradle.kts").write_text("")
        assert detect_build_tool(tmp_path) == BuildTool.GRADLE_KOTLIN

    def test_returns_none_when_no_build_file(self, tmp_path):
        assert detect_build_tool(tmp_path) is None


# ---------------------------------------------------------------------------
# detector — detect_java_version
# ---------------------------------------------------------------------------

class TestDetectJavaVersion:
    def test_detects_java17_maven(self, tmp_path):
        _make_pom(tmp_path, java_version="17")
        assert detect_java_version(tmp_path, BuildTool.MAVEN) == JavaVersion.V17

    def test_detects_java21_maven(self, tmp_path):
        _make_pom(tmp_path, java_version="21")
        assert detect_java_version(tmp_path, BuildTool.MAVEN) == JavaVersion.V21

    def test_detects_java25_maven(self, tmp_path):
        _make_pom(tmp_path, java_version="25")
        assert detect_java_version(tmp_path, BuildTool.MAVEN) == JavaVersion.V25

    def test_detects_java17_gradle(self, tmp_path):
        _make_gradle(tmp_path, java_version="17")
        assert detect_java_version(tmp_path, BuildTool.GRADLE_KOTLIN) == JavaVersion.V17

    def test_detects_java21_gradle(self, tmp_path):
        _make_gradle(tmp_path, java_version="21")
        assert detect_java_version(tmp_path, BuildTool.GRADLE_KOTLIN) == JavaVersion.V21

    def test_detects_java25_gradle(self, tmp_path):
        _make_gradle(tmp_path, java_version="25")
        assert detect_java_version(tmp_path, BuildTool.GRADLE_KOTLIN) == JavaVersion.V25

    def test_defaults_to_java21_when_not_found(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        assert detect_java_version(tmp_path, BuildTool.MAVEN) == JavaVersion.V21


# ---------------------------------------------------------------------------
# detector — detect_spring_boot_version
# ---------------------------------------------------------------------------

class TestDetectSpringBootVersion:
    def test_detects_sb_version_maven(self, tmp_path):
        _make_pom(tmp_path, sb_version="4.0.5")
        assert detect_spring_boot_version(tmp_path, BuildTool.MAVEN) == "4.0.5"

    def test_detects_sb_version_gradle(self, tmp_path):
        _make_gradle(tmp_path)
        assert detect_spring_boot_version(tmp_path, BuildTool.GRADLE_KOTLIN) == "4.0.5"

    def test_returns_none_when_not_found(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        assert detect_spring_boot_version(tmp_path, BuildTool.MAVEN) is None


# ---------------------------------------------------------------------------
# detector — detect_service_name
# ---------------------------------------------------------------------------

class TestDetectServiceName:
    def test_detects_from_pom(self, tmp_path):
        _make_pom(tmp_path)
        assert detect_service_name(tmp_path, BuildTool.MAVEN) == "my-service"

    def test_detects_from_gradle_settings(self, tmp_path):
        _make_gradle(tmp_path)
        assert detect_service_name(tmp_path, BuildTool.GRADLE_KOTLIN) == "my-service"

    def test_fallback_to_directory_name(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        assert detect_service_name(tmp_path, BuildTool.MAVEN) == tmp_path.name


# ---------------------------------------------------------------------------
# detector — detect_base_package
# ---------------------------------------------------------------------------

class TestDetectBasePackage:
    def test_detects_package(self, tmp_path):
        _make_spring_app(tmp_path, "com.example.payment")
        assert detect_base_package(tmp_path) == "com.example.payment"

    def test_returns_none_when_no_java_root(self, tmp_path):
        assert detect_base_package(tmp_path) is None

    def test_returns_none_when_no_spring_boot_app(self, tmp_path):
        java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
        java_dir.mkdir(parents=True)
        (java_dir / "Foo.java").write_text("package com.example;\npublic class Foo {}\n")
        assert detect_base_package(tmp_path) is None


# ---------------------------------------------------------------------------
# detector — detect_database
# ---------------------------------------------------------------------------

class TestDetectDatabase:
    def test_detects_postgresql(self, tmp_path):
        _make_pom(tmp_path, extra_deps="<dependency><artifactId>postgresql</artifactId></dependency>")
        assert detect_database(tmp_path, BuildTool.MAVEN) == Database.POSTGRESQL

    def test_detects_none_when_no_db(self, tmp_path):
        _make_pom(tmp_path)
        assert detect_database(tmp_path, BuildTool.MAVEN) == Database.NONE


# ---------------------------------------------------------------------------
# detector — has_dependency / has_otel_in_yml
# ---------------------------------------------------------------------------

class TestDetectorHelpers:
    def test_has_dependency_true(self, tmp_path):
        _make_pom(tmp_path, extra_deps="<artifactId>spring-boot-starter-opentelemetry</artifactId>")
        assert has_dependency(tmp_path, BuildTool.MAVEN, "spring-boot-starter-opentelemetry") is True

    def test_has_dependency_false(self, tmp_path):
        _make_pom(tmp_path)
        assert has_dependency(tmp_path, BuildTool.MAVEN, "spring-boot-starter-opentelemetry") is False

    def test_has_otel_in_yml_true(self, tmp_path):
        resources = tmp_path / "src" / "main" / "resources"
        resources.mkdir(parents=True)
        (resources / "application.yml").write_text("management:\n  otlp:\n    enabled: true\n")
        assert has_otel_in_yml(tmp_path) is True

    def test_has_otel_in_yml_false(self, tmp_path):
        resources = tmp_path / "src" / "main" / "resources"
        resources.mkdir(parents=True)
        (resources / "application.yml").write_text("spring:\n  application:\n    name: test\n")
        assert has_otel_in_yml(tmp_path) is False


# ---------------------------------------------------------------------------
# patcher — patch_pom_xml
# ---------------------------------------------------------------------------

class TestPatchPomXml:
    def test_adds_otel_deps(self, tmp_path):
        _make_pom(tmp_path)
        added = patch_pom_xml(tmp_path / "pom.xml")
        assert "spring-boot-starter-opentelemetry" in added
        assert "opentelemetry-logback-appender-1.0" in added

    def test_skips_existing_deps(self, tmp_path):
        _make_pom(tmp_path, extra_deps="<artifactId>spring-boot-starter-opentelemetry</artifactId>")
        added = patch_pom_xml(tmp_path / "pom.xml")
        assert "spring-boot-starter-opentelemetry" not in added

    def test_works_with_2space_indent(self, tmp_path):
        _make_pom(tmp_path, indent="  ")
        added = patch_pom_xml(tmp_path / "pom.xml")
        assert "spring-boot-starter-opentelemetry" in added
        content = (tmp_path / "pom.xml").read_text()
        assert "<dependency>" in content

    def test_works_with_tab_indent(self, tmp_path):
        _make_pom(tmp_path, indent="\t")
        added = patch_pom_xml(tmp_path / "pom.xml")
        assert "spring-boot-starter-opentelemetry" in added

    def test_patched_pom_is_valid_xml(self, tmp_path):
        import xml.etree.ElementTree as ET
        _make_pom(tmp_path)
        patch_pom_xml(tmp_path / "pom.xml")
        ET.parse(tmp_path / "pom.xml")  # raises if invalid


# ---------------------------------------------------------------------------
# patcher — patch_application_yml
# ---------------------------------------------------------------------------

class TestPatchApplicationYml:
    def test_creates_yml_when_absent(self, tmp_path):
        yml = tmp_path / "application.yml"
        result = patch_application_yml(yml)
        assert result == "created"
        assert yml.exists()
        assert "otlp" in yml.read_text()

    def test_patches_yml_without_management_key(self, tmp_path):
        yml = tmp_path / "application.yml"
        yml.write_text("spring:\n  application:\n    name: test\n")
        result = patch_application_yml(yml)
        assert result == "patched"
        content = yml.read_text()
        assert "management:" in content
        assert "otlp" in content

    def test_merges_into_existing_management_key(self, tmp_path):
        yml = tmp_path / "application.yml"
        yml.write_text(
            "spring:\n  application:\n    name: test\n\nmanagement:\n  server:\n    port: 8081\n"
        )
        result = patch_application_yml(yml)
        assert result == "patched"
        content = yml.read_text()
        # Must not have two top-level management: keys
        assert content.count("\nmanagement:") <= 1
        assert "otlp" in content

    def test_skips_when_already_configured(self, tmp_path):
        yml = tmp_path / "application.yml"
        yml.write_text("management:\n  otlp:\n    enabled: true\n")
        result = patch_application_yml(yml)
        assert result == "skipped"


# ---------------------------------------------------------------------------
# patcher — patch_build_file (gradle)
# ---------------------------------------------------------------------------

class TestPatchGradle:
    def test_adds_otel_deps_gradle(self, tmp_path):
        _make_gradle(tmp_path)
        added = patch_build_file(tmp_path, BuildTool.GRADLE_KOTLIN)
        assert "spring-boot-starter-opentelemetry" in added

    def test_skips_existing_deps_gradle(self, tmp_path):
        build = tmp_path / "build.gradle.kts"
        build.write_text(
            'dependencies {\n'
            '    implementation("org.springframework.boot:spring-boot-starter-opentelemetry")\n'
            '}\n'
        )
        added = patch_build_file(tmp_path, BuildTool.GRADLE_KOTLIN)
        assert "spring-boot-starter-opentelemetry" not in added

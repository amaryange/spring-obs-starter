"""Tests for the CLI — commands, validation, interactive flow."""
import pytest
from unittest.mock import patch
from click.testing import CliRunner

from cli.generate import main, _validate_service_count
from cli.models import (
    BuildTool,
    Database,
    DeploymentMode,
    JavaVersion,
    MetricsBackend,
    SPRING_BOOT_VERSION,
    SUPPORTED_SPRING_BOOT_VERSIONS,
    TargetEnvironment,
    TraceBackend,
)
from cli.validators import validate_service_name, validate_package


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _mock_create_answers(
    sb_version=None,
    build_tool=BuildTool.MAVEN,
    java_version=JavaVersion.V21,
    trace_backend=TraceBackend.TEMPO,
    deployment_mode=DeploymentMode.STANDALONE,
    metrics_backend=MetricsBackend.PROMETHEUS,
    database=Database.NONE,
    base_package="com.example.payment",
):
    """Returns (select_side_effects, text_side_effects) for patching questionary."""
    sb = sb_version or SUPPORTED_SPRING_BOOT_VERSIONS[0]
    selects = [sb, build_tool, java_version, trace_backend, deployment_mode, metrics_backend, database]
    texts = [base_package]
    return selects, texts


# ---------------------------------------------------------------------------
# Global flags
# ---------------------------------------------------------------------------

class TestGlobalFlags:
    def test_version_flag(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "sos" in result.output
        assert "Spring Boot" in result.output
        assert SPRING_BOOT_VERSION in result.output

    def test_no_subcommand_shows_banner(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "SOS" in result.output or "sos" in result.output.lower()
        assert "create" in result.output

    def test_help_flag(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "create" in result.output


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class TestValidators:
    # Service name
    def test_valid_service_names(self):
        for name in ["payment-service", "order", "my_api", "ServiceA"]:
            assert validate_service_name(name) is True

    def test_invalid_service_name_empty(self):
        assert validate_service_name("") is not True
        assert validate_service_name("   ") is not True

    def test_invalid_service_name_starts_with_digit(self):
        assert validate_service_name("1service") is not True

    def test_invalid_service_name_special_chars(self):
        assert validate_service_name("my service") is not True
        assert validate_service_name("my@service") is not True

    def test_service_name_too_long(self):
        assert validate_service_name("a" * 65) is not True
        assert validate_service_name("a" * 64) is True

    # Package name
    def test_valid_packages(self):
        for pkg in ["com.example.payment", "io.myapp.service", "org.a.b.c"]:
            assert validate_package(pkg) is True

    def test_invalid_package_single_segment(self):
        assert validate_package("payment") is not True

    def test_invalid_package_uppercase(self):
        assert validate_package("com.Example.payment") is not True

    def test_invalid_package_empty(self):
        assert validate_package("") is not True

    # Service count
    def test_valid_service_counts(self):
        for n in ["1", "5", "20"]:
            assert _validate_service_count(n) is True

    def test_invalid_service_count_zero(self):
        assert _validate_service_count("0") is not True

    def test_invalid_service_count_over_max(self):
        assert _validate_service_count("21") is not True

    def test_invalid_service_count_not_a_number(self):
        assert _validate_service_count("abc") is not True


# ---------------------------------------------------------------------------
# `sos create` — validation and flow
# ---------------------------------------------------------------------------

class TestCreate:
    def test_invalid_service_name_exits_with_error(self, runner):
        result = runner.invoke(main, ["create", "1invalid"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_valid_create_generates_project(self, runner, tmp_path):
        selects, texts = _mock_create_answers()

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ["create", "payment-service"])

        assert result.exit_code == 0
        assert "Project ready" in result.output

    def test_create_with_demo_flag(self, runner, tmp_path):
        selects, texts = _mock_create_answers()

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ["create", "payment-service", "--demo"])

        assert result.exit_code == 0
        assert "demo" in result.output.lower() or "Project ready" in result.output

    def test_create_multi_service_no_metrics_question(self, runner, tmp_path):
        """Metrics backend is NOT asked for multi-service mode."""
        selects = [
            SUPPORTED_SPRING_BOOT_VERSIONS[0],
            BuildTool.MAVEN,
            JavaVersion.V21,
            TraceBackend.TEMPO,
            DeploymentMode.MULTI_SERVICE,  # no metrics question follows
            Database.NONE,
        ]
        texts = ["com.example.payment"]

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ["create", "payment-service"])

        assert result.exit_code == 0

    def test_create_shows_grafana_endpoint_for_standalone(self, runner, tmp_path):
        selects, texts = _mock_create_answers()

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ["create", "payment-service"])

        assert "Grafana" in result.output
        assert "3000" in result.output

    def test_create_shows_jaeger_endpoint(self, runner, tmp_path):
        selects, texts = _mock_create_answers(trace_backend=TraceBackend.JAEGER)

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ["create", "payment-service"])

        assert "Jaeger" in result.output
        assert "16686" in result.output

    def test_create_aborts_if_dir_exists_and_refused(self, runner, tmp_path):
        selects, texts = _mock_create_answers()

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text, \
             patch("questionary.confirm") as mock_confirm:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts
            mock_confirm.return_value.ask.return_value = False

            with runner.isolated_filesystem(temp_dir=tmp_path):
                import os
                os.makedirs("payment-service")
                result = runner.invoke(main, ["create", "payment-service"])

        assert result.exit_code == 0
        assert "Aborted" in result.output


# ---------------------------------------------------------------------------
# `sos create-stack`
# ---------------------------------------------------------------------------

class TestCreateStack:
    def test_invalid_stack_name_exits_with_error(self, runner):
        result = runner.invoke(main, ["create-stack", "1invalid"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_valid_create_stack(self, runner, tmp_path):
        selects = [
            SUPPORTED_SPRING_BOOT_VERSIONS[0],  # sb version (shared)
            TraceBackend.TEMPO,                  # trace backend (shared)
            MetricsBackend.PROMETHEUS,           # metrics backend (shared)
            # service 1
            BuildTool.MAVEN,
            JavaVersion.V21,
            Database.NONE,
            # service 2
            BuildTool.MAVEN,
            JavaVersion.V21,
            Database.NONE,
        ]
        texts = [
            "2",                       # num services
            "order-service",           # service 1 name
            "com.example.order",       # service 1 package
            "payment-service",         # service 2 name
            "com.example.payment",     # service 2 package
        ]

        with patch("questionary.select") as mock_select, \
             patch("questionary.text") as mock_text:
            mock_select.return_value.ask.side_effect = selects
            mock_text.return_value.ask.side_effect = texts

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(main, ["create-stack", "ecommerce-stack"])

        assert result.exit_code == 0
        assert "ready" in result.output.lower()


# ---------------------------------------------------------------------------
# Models — SUPPORTED_SPRING_BOOT_VERSIONS
# ---------------------------------------------------------------------------

class TestVersionConstants:
    def test_spring_boot_version_is_latest(self):
        assert SPRING_BOOT_VERSION == SUPPORTED_SPRING_BOOT_VERSIONS[0]

    def test_supported_versions_are_sorted_desc(self):
        versions = SUPPORTED_SPRING_BOOT_VERSIONS
        parsed = [[int(x) for x in v.split(".")] for v in versions]
        assert parsed == sorted(parsed, reverse=True)

    def test_supported_versions_count(self):
        assert len(SUPPORTED_SPRING_BOOT_VERSIONS) >= 4

    def test_no_snapshot_or_rc_versions(self):
        for v in SUPPORTED_SPRING_BOOT_VERSIONS:
            assert "SNAPSHOT" not in v
            assert "RC" not in v
            assert "M" not in v.split(".")[-1]

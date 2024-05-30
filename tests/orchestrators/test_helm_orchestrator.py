#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for the HelmOrchestrator.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

# Standard imports.
from pathlib import Path
import subprocess

# Vendor imports.
import pytest

# Local imports.
from appcli.models.cli_context import CliContext
from appcli.orchestrators import HelmOrchestrator


# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "Test App"
APP_NAME_SLUG = "TEST_APP"

# directory containing this script
BASE_DIR = Path(__file__).parent


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


@pytest.fixture
def cli_context(tmp_path) -> CliContext:
    conf_dir: Path = BASE_DIR / "conf"
    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    backup_dir: Path = tmp_path / "backup"
    backup_dir.mkdir()

    return CliContext(
        configuration_dir=conf_dir,
        data_dir=data_dir,
        application_context_files_dir=None,
        additional_data_dirs=None,
        backup_dir=backup_dir,
        additional_env_variables=None,
        environment="test",
        docker_credentials_file=None,
        subcommand_args=None,
        debug=True,
        is_dev_mode=False,
        app_name_slug=APP_NAME_SLUG,
        app_version="0.0.0",
        commands=None,
    )


@pytest.fixture
def default_orchestrator() -> HelmOrchestrator:
    return HelmOrchestrator()


@pytest.fixture
def modified_orchestrator() -> HelmOrchestrator:
    return HelmOrchestrator(
        chart_location="cli/helm/mychart.tgz",
        helm_set_values_dir="cli/helm/custom-set-values",
        helm_set_files_dir="cli/helm/custom-set-files",
    )


@pytest.fixture(autouse=True)
def monkeypatch_subprocess(monkeypatch):
    """Monkeypatch the `subprocess.run` method, so we do not actually call it."""

    def patched_subprocess_run(command, capture_output=True, input=None):
        return subprocess.CompletedProcess(returncode=0, args=command)

    monkeypatch.setattr(subprocess, "run", patched_subprocess_run)


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


class Test_HelmOrchestrator:
    def test_service_stop(
        self, default_orchestrator: HelmOrchestrator, cli_context: CliContext
    ):
        result = default_orchestrator.shutdown(cli_context)

        assert "helm" == result.args[0]
        assert "uninstall" == result.args[1]
        assert "test-app-test" in result.args

    def test_service_status(
        self, default_orchestrator: HelmOrchestrator, cli_context: CliContext
    ):
        result = default_orchestrator.status(cli_context)

        assert "helm" == result.args[0]
        assert "status" == result.args[1]
        assert "test-app-test" in result.args

    def test_service_start(
        self, default_orchestrator: HelmOrchestrator, cli_context: CliContext
    ):
        result = default_orchestrator.start(cli_context)

        assert "helm" == result.args[0]
        assert "upgrade" == result.args[1]
        assert "test-app-test" in result.args
        # NOTE: Last arg is chart path.
        assert str(result.args[-1]).endswith("cli/helm/chart")

    def test_modified_orchestrator(
        self, modified_orchestrator: HelmOrchestrator, cli_context: CliContext
    ):
        result = modified_orchestrator.start(cli_context)
        conf_dir = cli_context.get_generated_configuration_dir()

        # `--values` args.
        assert f"{conf_dir}/cli/helm/custom-set-values/values.yml" in result.args

        # `--set-file` args.
        assert f"top={conf_dir}/cli/helm/custom-set-files/top.yaml" in result.args
        assert (
            f"nested.nested={conf_dir}/cli/helm/custom-set-files/nested/nested.yaml"
            in result.args
        )

        # NOTE: Last arg is chart path.
        assert str(result.args[-1]).endswith("cli/helm/mychart.tgz")

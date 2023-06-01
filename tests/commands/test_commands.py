#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for Commands.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import subprocess
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner

# vendor libraries
from ruamel.yaml import YAML

# local libraries
from appcli.commands.configure_cli import ConfigureCli
from appcli.commands.service_cli import ServiceCli
from appcli.configuration_manager import ConfigurationManager
from appcli.logger import enable_debug_logging, logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.orchestrators import DockerComposeOrchestrator

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "Test App"
APP_NAME_SLUG = "Test_App"

# directory containing this script
BASE_DIR = Path(__file__).parent

STACK_CONFIGURATION_FILE = Path(BASE_DIR, "resources/test_stack_settings.yml")

DOCKER_COMPOSE_YML = Path(BASE_DIR, "resources/templates/baseline/docker-compose.yml")

DOCKER_COMPOSE_SERVICES = list(YAML().load(open(DOCKER_COMPOSE_YML))["services"].keys())

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


class Test_ServiceCommands:
    # --------------------------------------------------------------------------
    # SERVICE START
    # --------------------------------------------------------------------------

    def test_service_start_no_input(self, test_env):
        result = test_env.invoke_service_command(["start"])

        assert "force is [False]" in result.output
        assert f"START {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_start_single_input(self, test_env):
        result = test_env.invoke_service_command(["start", "service_2"])

        assert "force is [False]" in result.output
        assert "START service_2 ..." in result.output
        assert result.exit_code == 0

    def test_service_start_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(["start", "service_2", "service_1"])

        assert "force is [False]" in result.output
        assert "START service_2, service_1 ..." in result.output
        assert result.exit_code == 0

    def test_service_start_invalid_input(self, test_env):
        result = test_env.invoke_service_command(
            ["start", "INVALID_SERVICE_1", "service_1", "INVALID_SERVICE_2"]
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert "Service [INVALID_SERVICE_2] does not exist" in result.output
        assert result.exit_code == 1

    def test_service_start_force_flag_no_inputs(self, test_env):
        result = test_env.invoke_service_command(["start", "--force"])

        assert "force is [True]" in result.output
        assert f"START {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_start_force_flag_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["start", "--force", "service_1", "service_2", "service_3"],
        )

        assert "force is [True]" in result.output
        assert "START service_1, service_2, service_3 ..." in result.output
        assert result.exit_code == 0

    def test_service_start_force_flag_invalid_inputs(self, test_env):
        result = test_env.invoke_service_command(
            [
                "start",
                "--force",
                "service_1",
                "service_1",
                "INVALID_SERVICE_1",
                "INVALID_SERVICE_2",
            ],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert "Service [INVALID_SERVICE_2] does not exist" in result.output
        assert result.exit_code == 1

    # --------------------------------------------------------------------------
    # SERVICE SHUTDOWN
    # --------------------------------------------------------------------------

    def test_service_shutdown_no_input(self, test_env):
        result = test_env.invoke_service_command(["shutdown"])

        assert f"SHUTDOWN {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_shutdown_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["shutdown", "service_3", "service_1"],
        )

        assert "SHUTDOWN service_3, service_1 ..." in result.output
        assert result.exit_code == 0

    def test_service_shutdown_invalid_input(self, test_env):
        result = test_env.invoke_service_command(
            ["shutdown", "service_1", "service_2", "INVALID_SERVICE_1"],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert result.exit_code == 1

    # --------------------------------------------------------------------------
    # SERVICE RESTART
    # --------------------------------------------------------------------------

    def test_service_restart_no_input(self, test_env):
        result = test_env.invoke_service_command(["restart"])

        assert "force is [False]" in result.output
        assert f"SHUTDOWN {APP_NAME} ..." in result.output
        assert f"START {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_single_input(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "service_1"],
        )

        assert "force is [False]" in result.output
        assert "SHUTDOWN service_1 ..." in result.output
        assert "START service_1 ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "service_1", "service_2"],
        )

        assert "force is [False]" in result.output
        assert "SHUTDOWN service_1, service_2 ..." in result.output
        assert "START service_1, service_2 ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_invalid_input(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "service_1", "service_2", "INVALID_SERVICE_1"],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert result.exit_code == 1

    def test_service_restart_force_flag_no_inputs(self, test_env):
        result = test_env.invoke_service_command(["restart", "--force"])

        assert "force is [True]" in result.output
        assert f"SHUTDOWN {APP_NAME} ..." in result.output
        assert f"START {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_force_flag_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "--force", "service_1", "service_2"],
        )

        assert "force is [True]" in result.output
        assert "SHUTDOWN service_1, service_2 ..." in result.output
        assert "START service_1, service_2 ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_force_flag_invalid_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "--force", "INVALID_SERVICE_1", "service_1", "service_2"],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert result.exit_code == 1

    def test_service_restart_apply_flag_no_inputs(self, test_env):
        result = test_env.invoke_service_command(["restart", "--apply"])
        print(result.output)

        assert "force is [False]" in result.output
        assert "Finished applying configuration" in result.output
        assert f"SHUTDOWN {APP_NAME} ..." in result.output
        assert f"START {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_apply_flag_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "--apply", "service_1", "service_2"],
        )

        assert "force is [False]" in result.output
        assert "Finished applying configuration" in result.output
        assert "SHUTDOWN service_1, service_2 ..." in result.output
        assert "START service_1, service_2 ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_apply_flag_invalid_inputs(self, test_env):
        result = test_env.invoke_service_command(
            [
                "restart",
                "--apply",
                "INVALID_SERVICE_1",
                "service_1",
                "service_2",
                "INVALID_SERVICE_2",
            ],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert "Service [INVALID_SERVICE_2] does not exist" in result.output
        assert result.exit_code == 1

    def test_service_restart_force_apply_flag_no_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "--force", "--apply"],
        )

        assert "force is [True]" in result.output
        assert "Finished applying configuration" in result.output
        assert f"SHUTDOWN {APP_NAME} ..." in result.output
        assert f"START {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_force_apply_flag_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["restart", "--force", "--apply", "service_1", "service_2"],
        )

        assert "force is [False]" in result.output
        assert "Finished applying configuration" in result.output
        assert "SHUTDOWN service_1, service_2 ..." in result.output
        assert "START service_1, service_2 ..." in result.output
        assert result.exit_code == 0

    def test_service_restart_force_apply_flag_invalid_inputs(self, test_env):
        result = test_env.invoke_service_command(
            [
                "restart",
                "--force",
                "--apply",
                "INVALID_SERVICE_1",
                "service_1",
                "service_2",
                "INVALID_SERVICE_2",
            ],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert "Service [INVALID_SERVICE_2] does not exist" in result.output
        assert result.exit_code == 1

    # --------------------------------------------------------------------------
    # SERVICE STATUS
    # --------------------------------------------------------------------------
    def test_service_status_no_input(self, test_env):
        result = test_env.invoke_service_command(["status"])

        assert f"STATUS {APP_NAME} ..." in result.output
        assert result.exit_code == 0

    def test_service_status_single_input(self, test_env):
        result = test_env.invoke_service_command(["status", "service_2"])

        assert "STATUS service_2 ..." in result.output
        assert result.exit_code == 0

    def test_service_status_multiple_inputs(self, test_env):
        result = test_env.invoke_service_command(
            ["status", "service_3", "service_1"],
        )

        assert "STATUS service_3, service_1 ..." in result.output
        assert result.exit_code == 0

    def test_service_status_invalid_input(self, test_env):
        result = test_env.invoke_service_command(
            ["status", "service_1", "service_2", "INVALID_SERVICE_1"],
        )

        assert "Service [INVALID_SERVICE_1] does not exist" in result.output
        assert result.exit_code == 1


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    return Environment(tmp_path_factory)


@pytest.fixture(autouse=True)
def patch_subprocess(monkeypatch):
    def patched_subprocess_run(docker_compose_command, capture_output=True, input=None):
        # TODO: We should take advantage of the printed command to perform test validation
        logger.info(f"PYTEST_PATCHED_DOCKER_COMPOSE_COMMAND=[{docker_compose_command}]")
        if all([x in docker_compose_command for x in ["config", "--services"]]):
            # patch for fetching the valid service names, used by the verify_service_names orchestrator.
            valid_services = "\n".join(DOCKER_COMPOSE_SERVICES) + "\n"
            return subprocess.CompletedProcess(
                returncode=0, args=None, stdout=bytes(valid_services, "utf-8")
            )
        elif all([x in docker_compose_command for x in ["up", "-d"]]):
            # patch for starting all services, used by the start orchestrator.
            return subprocess.CompletedProcess(returncode=0, args=None)
        elif all([x in docker_compose_command for x in ["down"]]):
            # patch for shutting down all services, used by the shutdown orchestrator for shutting down all services.
            return subprocess.CompletedProcess(returncode=0, args=None)
        elif all([x in docker_compose_command for x in ["rm", "-fsv"]]):
            # patch for shutting down all services, used by the shutdown orchestrator when given provided with specific services.
            return subprocess.CompletedProcess(returncode=0, args=None)
        elif all([x in docker_compose_command for x in ["ps", "-a"]]):
            # patch for getting the status of all services, used by the status orchestrator for getting the status all services.
            return subprocess.CompletedProcess(returncode=0, args=None)
        else:
            # patch for unknown command action
            print("Unknown command: %s", docker_compose_command)
            return subprocess.CompletedProcess(returncode=1, args=None)

    monkeypatch.setattr(subprocess, "run", patched_subprocess_run)


class Environment:
    """The test appcli environment in which we can run commands."""

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, tmpdir) -> None:
        enable_debug_logging()
        self.config = self._create_config()
        self.cli_context = self._create_cli_context(tmpdir, self.config)
        self.config_manager = self._create_config_manager(self.cli_context, self.config)
        self.config_manager.initialise_configuration()
        self.config_manager.apply_configuration_changes(message="init apply")
        self.runner = CliRunner()

    # --------------------------------------------------------------------------
    # PUBLIC METHODS
    # --------------------------------------------------------------------------

    def invoke_service_command(self, args: List[str]):
        return self.runner.invoke(
            ServiceCli(self.config).commands["service"],
            args,
            obj=self.cli_context,
        )

    # --------------------------------------------------------------------------
    # PRIVATE METHODS
    # --------------------------------------------------------------------------

    def _create_cli_context(self, tmpdir, config) -> CliContext:
        group_dir = str(tmpdir.mktemp("commands_test"))
        conf_dir = Path(group_dir, "conf")
        conf_dir.mkdir(exist_ok=True)
        data_dir = Path(group_dir, "data")
        data_dir.mkdir(exist_ok=True)
        backup_dir = Path(group_dir, "backup")
        backup_dir.mkdir(exist_ok=True)
        templates_dir = Path(group_dir, "conf/templates")
        templates_dir.mkdir(exist_ok=True)
        appcli_dir = Path(group_dir, "conf/templates/appcli")
        appcli_dir.mkdir(exist_ok=True)
        context_dir = Path(group_dir, "conf/templates/appcli/context")
        context_dir.mkdir(exist_ok=True)

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
            app_name_slug=APP_NAME,
            app_version="0.0.0",
            commands=ConfigureCli(config).commands,
        )

    def _create_config(self) -> Configuration:
        return Configuration(
            app_name=APP_NAME,
            docker_image="invalid-image-name",
            seed_app_configuration_file=Path(BASE_DIR, "resources/test_app.yml"),
            baseline_templates_dir=Path(BASE_DIR, "resources/templates/baseline"),
            configurable_templates_dir=Path(
                BASE_DIR, "resources/templates/configurable"
            ),
            orchestrator=DockerComposeOrchestrator(),
            stack_configuration_file=STACK_CONFIGURATION_FILE,
        )

    def _create_config_manager(
        self, cli_context: CliContext, config: Configuration
    ) -> ConfigurationManager:
        return ConfigurationManager(cli_context, config)

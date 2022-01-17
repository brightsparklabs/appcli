#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for Task Commands.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import subprocess
from pathlib import Path
from time import sleep, time
from typing import List

import pytest
from click.testing import CliRunner

# vendor libraries
from ruamel.yaml import YAML

# local libraries
from appcli.commands.configure_cli import ConfigureCli
from appcli.commands.task_cli import TaskCli
from appcli.configuration_manager import ConfigurationManager
from appcli.logger import enable_debug_logging, logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.orchestrators import DockerComposeOrchestrator

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "TEST_APP"

# directory containing this script
BASE_DIR = Path(__file__).parent

STACK_CONFIGURATION_FILE = Path(BASE_DIR, "resources/test_stack_settings.yml")

DOCKER_COMPOSE_YML = Path(
    BASE_DIR, "resources/templates/baseline/docker-compose.tasks.yml"
)

DOCKER_COMPOSE_SERVICES = list(YAML().load(open(DOCKER_COMPOSE_YML))["services"].keys())

# ------------------------------------------------------------------------------
# TASKS
# ------------------------------------------------------------------------------


class Test_TaskCommands:
    def test_task_run_headless_arg_long(self, test_env):

        TIME_START = time()
        result = test_env.invoke_task_command(["run", "--detach", "sleep-1"])
        TIME_END = time()

        assert TIME_END - TIME_START < 0.1
        assert result.exit_code == 0

    def test_task_run_headless_arg_short(self, test_env):

        TIME_START = time()
        result = test_env.invoke_task_command(["run", "-d", "sleep-1"])
        TIME_END = time()

        assert TIME_END - TIME_START < 0.1
        assert result.exit_code == 0

    def test_task_run_not_headless(self, test_env):

        TIME_START = time()
        result = test_env.invoke_task_command(["run", "sleep-1"])
        TIME_END = time()

        assert TIME_END - TIME_START > 0.1
        assert result.exit_code == 0


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    return Environment(tmp_path_factory)


@pytest.fixture(autouse=True)
def patch_subprocess(monkeypatch):
    def patched_subprocess_run(docker_compose_command, capture_output=True):
        # TODO: We should take advantage of the printed command to perform test validation
        logger.info(f"PYTEST_PATCHED_DOCKER_COMPOSE_COMMAND=[{docker_compose_command}]")
        if not any([x in docker_compose_command for x in ["--detach", "-d"]]):
            # patch for running in standard mode.
            sleep(0.1)
            return subprocess.CompletedProcess(returncode=0, args=None)
        elif all([x in docker_compose_command for x in ["-d"]]):
            # patch for run headless/detached
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

    def invoke_task_command(self, args: List[str]):
        return self.runner.invoke(
            TaskCli(self.config).commands["task"],
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

        return CliContext(
            configuration_dir=conf_dir,
            data_dir=data_dir,
            additional_data_dirs=None,
            backup_dir=backup_dir,
            additional_env_variables=None,
            environment="test",
            docker_credentials_file=None,
            subcommand_args=None,
            debug=True,
            app_name=APP_NAME,
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

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for Services Commands.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

from appcli.configuration_manager import ConfigurationManager
from click.decorators import command
import pytest
import click
from pathlib import Path, PurePath
from click.testing import CliRunner
from appcli.commands.service_cli import ServiceCli
from appcli.logger import enable_debug_logging

from appcli.models.configuration import Configuration
from appcli.models.cli_context import CliContext
from appcli.orchestrators import DockerComposeOrchestrator

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "test_app"

# directory containing this script
BASE_DIR = Path(__file__).parent

STACK_CONFIGURATION_FILE = Path(BASE_DIR, "resources/test_stack_settings.yml")

DOCKER_COMPOSE = Path("docker-compose.yml")

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_service_start_no_input(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["start"], obj=cli_context)

    print(result.output)
    print("result-exit_code", result.exit_code)

    assert "force is [False]" in result.output
    assert ("Starting %s ...",APP_NAME) in result.output
    assert result.exit_code == 0


def test_service_start_multiple_inputs(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()   

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["start","service_1", "service_2"], obj=cli_context)

    assert "force is [False]" in result.output
    assert "Starting service_1 ..." in result.output
    assert "Starting service_2 ..." in result.output
    assert result.exit_code == 0


def test_service_start_invalid_input(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["start","INVALID_SERVICE_1", "service_1","INVALID_SERVICE_2"], obj=cli_context)

    assert "force is [False]" in result.output
    assert "Service [INVALID_SERVICE_1] does not exist" in result.output
    assert "Service [INVALID_SERVICE_2] does not exist" in result.output
    assert result.exit_code == 1

def test_service_start_force_flag_no_inputs(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["start","--force"], obj=cli_context)

    assert "force is [True]" in result.output
    assert ("Starting %s ...",APP_NAME) in result.output
    assert result.exit_code == 0

def test_service_start_force_flag_multiple_inputs(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["start","--force","service_1","service_2","service_3"],obj=cli_context)

    assert "force is [True]" in result.output
    assert "Starting service_1..." in result.output
    assert "Starting service_2..." in result.output
    assert "Starting service_3..." in result.output
    assert result.exit_code == 0

def test_service_start_force_flag_invalid_inputs(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["start","--force","service_1","service_1","INVALID_SERVICE_1","INVALID_SERVICE_2"],obj=cli_context)

    assert "force is [True]" in result.output
    assert "Service [INVALID_SERVICE_1] does not exist" in result.output
    assert "Service [INVALID_SERVICE_2] does not exist" in result.output
    assert result.exit_code == 1


def test_service_shutdown_no_input(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["shutdown"],obj=cli_context)

    assert result.exit_code == 0
    

def test_service_shutdown_multiple_inputs(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["shutdown","service_3","service_1"],obj=cli_context)

    assert result.exit_code == 0

def test_service_shutdown_invalid_input(tmpdir):
    enable_debug_logging()
    cli_context = create_cli_context(tmpdir)
    config = create_config(tmpdir, cli_context)
    config_manager = create_config_manager(cli_context, config)
    config_manager.initialise_configuration()
    config_manager.apply_configuration_changes(message="init apply")
    runner = CliRunner()

    service_command = ServiceCli(config).commands["service"]
    result = runner.invoke(service_command, ["shutdown","service_1","service_2","INVALID"],obj=cli_context)

    assert result.exit_code == 1


def test_service_restart_no_input():
    pass

def test_service_restart_multiple_inputs():
    pass

def test_service_restart_invalid_input():
    pass

def test_service_restart_force_flag_no_inputs():
    pass

def test_service_restart_force_flag_multiple_inputs():
    pass

def test_service_restart_force_flag_invalid_inputs():
    pass



# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_cli_context(tmpdir) -> CliContext:
    conf_dir = Path(tmpdir, "conf")
    conf_dir.mkdir(exist_ok=True)
    data_dir = Path(tmpdir, "data")
    data_dir.mkdir(exist_ok=True)
    backup_dir = Path(tmpdir, "backup")
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
        commands={},
    )


def create_config(tmpdir, cli_context: CliContext) -> Configuration:
    return Configuration(
        app_name=APP_NAME,
        docker_image="invalid-image-name",
        seed_app_configuration_file=Path(BASE_DIR, "resources/test_app.yml"),
        baseline_templates_dir=Path(BASE_DIR, "resources/templates/baseline"),
        configurable_templates_dir=Path(BASE_DIR, "resources/templates/configurable"),
        orchestrator=DockerComposeOrchestrator(DOCKER_COMPOSE, []),
        stack_configuration_file=STACK_CONFIGURATION_FILE,
    )


def create_config_manager(
    cli_context: CliContext, config: Configuration
) -> ConfigurationManager:
    return ConfigurationManager(cli_context, config)

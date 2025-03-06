#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for Preset Configuration.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# Standard imports.
from pathlib import Path

# Vendor imports.
import pytest
from click.testing import CliRunner

# Local imports.
from appcli.commands.configure_cli import ConfigureCli
from appcli.models.configuration import Configuration
from appcli.models.cli_context import CliContext


# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# Directory containing source config files.
RESOURCES_DIR = Path(__file__).parent / "resources"
TEMPLATES_DIR = RESOURCES_DIR / "templates"


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


@pytest.fixture
def default_configuration():
    return Configuration(
        app_name="myapp",
        docker_image="myapp/myapp",
        seed_app_configuration_file=RESOURCES_DIR / "settings.yml",
        stack_configuration_file=RESOURCES_DIR / "stack-settings.yml",
        baseline_templates_dir=TEMPLATES_DIR / "baseline",
        configurable_templates_dir=TEMPLATES_DIR / "configurable",
        auto_configure_on_install=False,
    )


@pytest.fixture
def preset_configuration(default_configuration):
    default_configuration.presets.is_mandatory = True
    default_configuration.presets.templates_directory = TEMPLATES_DIR / "presets"
    return default_configuration


@pytest.fixture
def default_cli_context(tmp_path):
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    return CliContext(
        configuration_dir=conf_dir,
        data_dir=data_dir,
        backup_dir=backup_dir,
        application_context_files_dir=app_dir,
        additional_data_dirs=[],
        additional_env_variables=[],
        environment="dev",
        docker_credentials_file=None,
        subcommand_args=[],
        debug=True,
        is_dev_mode=True,
        app_name_slug="myapp",
        app_version="0.0.0",
        commands={},
    )


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_unconfigured_preset(default_configuration, default_cli_context):
    """Test the systems still runs without configuring `preset` for legacy support."""
    cli = ConfigureCli(default_configuration)
    command = cli.commands["configure"].commands["init"]
    runner = CliRunner()
    runner.invoke(command, obj=default_cli_context)

    templates_dir = default_cli_context.configuration_dir / "templates"
    assert (templates_dir / "foo.txt").is_file()
    assert "default data" in (templates_dir / "foo.txt").read_text()


def test_default_preset(preset_configuration, default_cli_context):
    """Test that a default preset will be applied."""
    preset_configuration.presets.default_preset = "preset1"
    cli = ConfigureCli(preset_configuration)
    command = cli.commands["configure"].commands["init"]
    runner = CliRunner()
    runner.invoke(command, obj=default_cli_context)

    templates_dir = default_cli_context.configuration_dir / "templates"
    # Check that we do not just blow away any files that already exist.
    assert (templates_dir / "foo.txt").is_file()
    assert (templates_dir / "bar.txt").is_file()  # Preset-specific file.


def test_cli_preset(preset_configuration, default_cli_context):
    """Test whether we can supply a preset through the cli arg."""
    cli = ConfigureCli(preset_configuration)
    command = cli.commands["configure"].commands["init"]
    runner = CliRunner()
    runner.invoke(command, ["--preset", "preset1"], obj=default_cli_context)

    templates_dir = default_cli_context.configuration_dir / "templates"
    # Check that we do not just blow away any files that already exist.
    assert (templates_dir / "foo.txt").is_file()
    assert (templates_dir / "bar.txt").is_file()  # Preset-specific file.


def test_preset_overwrite(preset_configuration, default_cli_context):
    """Test preset-specific files will overwrite configurable ones."""
    cli = ConfigureCli(preset_configuration)
    command = cli.commands["configure"].commands["init"]
    runner = CliRunner()
    runner.invoke(command, ["--preset", "preset2"], obj=default_cli_context)

    templates_dir = default_cli_context.configuration_dir / "templates"
    assert (templates_dir / "foo.txt").is_file()
    assert "overwrite data" in (templates_dir / "foo.txt").read_text()


def test_preset_required(preset_configuration, default_cli_context):
    """Test that a preset is required."""
    cli = ConfigureCli(preset_configuration)
    command = cli.commands["configure"].commands["init"]
    runner = CliRunner()
    result = runner.invoke(command, obj=default_cli_context)
    result_text = result.stdout_bytes.decode("utf-8")

    assert result.exit_code == 2
    assert "Missing option '--preset' / '-p'" in result_text
    # Also check expected profiles.
    assert "Choose from:" in result_text
    assert "preset1" in result_text
    assert "preset2" in result_text


def test_invalid_preset(preset_configuration, default_cli_context):
    """Test supplying a preset that does not exist."""
    cli = ConfigureCli(preset_configuration)
    command = cli.commands["configure"].commands["init"]
    runner = CliRunner()
    result = runner.invoke(command, ["--preset", "preset3"], obj=default_cli_context)
    result_text = result.stdout_bytes.decode("utf-8")

    assert result.exit_code == 2
    assert "Invalid value for '--preset' / '-p'" in result_text

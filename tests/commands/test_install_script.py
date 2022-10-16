#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for checking the outputted install script.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
from pathlib import Path

# local libraries
from appcli.models.configuration import Configuration
from appcli.orchestrators import DockerComposeOrchestrator

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_install_autoconfig_default(self):
    """Check if autoconfig defaults to `True` when unspecified."""
    assert create_configuration().auto_configure_on_install is True


def test_install_autoconfig_false(self):
    """Check if autoconfig can be set to `False`."""
    assert create_configuration(False).auto_configure_on_install is False


def test_install_autoconfig_cli(self):
    """Check if autoconfig can be overwritten by providing
    `--auto-configure=false` to the cli.
    """
    # TODO: Find an easy way to test ths.
    pass


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------

def create_configuration(auto_configure_on_install: bool = None) -> Configuration:

    if auto_configure_on_install is None:
        return Configuration(
            app_name="my-app",
            docker_image="invalid-image-name",
            seed_app_configuration_file=Path("resources/test_app.yml"),
            baseline_templates_dir=Path("resources/templates/baseline"),
            configurable_templates_dir=Path("resources/templates/configurable"),
            orchestrator=DockerComposeOrchestrator("cli/docker-compose.yml", []),
            stack_configuration_file=Path("resources/stack-configuration.yml"),
        )
    else:
        return Configuration(
            app_name="my-app",
            docker_image="invalid-image-name",
            seed_app_configuration_file=Path("resources/test_app.yml"),
            baseline_templates_dir=Path("resources/templates/baseline"),
            configurable_templates_dir=Path("resources/templates/configurable"),
            orchestrator=DockerComposeOrchestrator("cli/docker-compose.yml", []),
            stack_configuration_file=Path("resources/stack-configuration.yml"),
            auto_configure_on_install=auto_configure_on_install
        )

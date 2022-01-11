#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for Configuration.
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
# TESTS
# ------------------------------------------------------------------------------


def test_app_name_capitalises():
    # Capitalises
    assert create_configuration("abc").app_name == "ABC"


def test_app_name_replaces_leading_digits():
    # Replaces starting number with underscore
    assert create_configuration("123abc").app_name == "_23ABC"


def test_app_name_replaces_invalid_characters():
    # Replaces unknown characters
    assert create_configuration("a-B=c+D$e#f").app_name == "A_B_C_D_E_F"
    assert (
        create_configuration("abc~!@#$%^&*()_+`-=[]{}|;':,./<>?def").app_name
        == "ABC______________________________DEF"
    )


# TODO: Further dev and tests:
# - how should we handle if an app_name has no alphanumeric characters? Should the name be all '_'?
# - how should we handle empty string app_name?

# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_configuration(app_name: str) -> Configuration:

    return Configuration(
        app_name=app_name,
        docker_image="invalid-image-name",
        seed_app_configuration_file=Path("resources/test_app.yml"),
        baseline_templates_dir=Path("resources/templates/baseline"),
        configurable_templates_dir=Path("resources/templates/configurable"),
        orchestrator=DockerComposeOrchestrator("cli/docker-compose.yml", []),
        stack_configuration_file=Path("resources/stack-configuration.yml"),
    )

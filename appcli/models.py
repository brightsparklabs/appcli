#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

from types import LambdaType, FunctionType
from typing import NamedTuple, List
from pathlib import Path


class ConfigSetting(NamedTuple):
    path: str
    message: str
    validate: LambdaType = lambda _, x: True


class ConfigSettingsGroup(NamedTuple):
    title: str
    settings: List[ConfigSetting]


class ConfigCli(NamedTuple):
    settings_groups: List[ConfigSettingsGroup]


class Configuration(NamedTuple):
    """
    Configuration for building the CLI.
    """

    app_name: str
    """ Name of the application (do not use spaces). """

    docker_image: str
    """ The docker image used to run the CLI. """

    app_configuration_file: Path
    """
    Path to a YAML file containing variables which are applied to the
    templates to generate the final configuration files.
    """

    templates_dir: Path
    """
    Directory containing jinja2 templates used to generate the final
    configuration files.
    """

    #apply_configuration_settings_callback: FunctionType
    #config_cli: ConfigCli
    #pre_configuration_callback: FunctionType = lambda *a, **k: None


class CliContext(NamedTuple):
    """
    Shared context from a run of the CLI.
    """

    configuration_dir: Path
    """ Directory to read configuration files from """

    generated_configuration_dir: Path
    """ Directory to store the generated configuration files to """

    data_dir: Path
    """ Directory to store data to """

    subcommand_args: tuple
    """ Arguments passed to CLI subcommand """

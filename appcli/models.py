#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

from types import LambdaType, FunctionType
from typing import Callable, NamedTuple, List
from pathlib import Path


class CliContext(NamedTuple):
    """
    Shared context from a run of the CLI.
    """

    configuration_dir: Path
    """ Directory to read configuration files from """

    data_dir: Path
    """ Directory to store data to """

    subcommand_args: tuple
    """ Arguments passed to CLI subcommand """

    generated_configuration_dir: Path
    """ Directory to store the generated configuration files to """

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

    debug: bool
    """ Whether to print debug logs """


class ConfigSetting(NamedTuple):
    path: str
    message: str
    validate: LambdaType = lambda _, x: True


class ConfigSettingsGroup(NamedTuple):
    title: str
    settings: List[ConfigSetting]

class Hooks(NamedTuple):
    pre_configure: Callable[[CliContext], None] = lambda x: None
    """ Hook to run before running configure. """
    post_configure: Callable[[CliContext], None] = lambda x: None
    """ Hook to run after running configure. """
    pre_apply: Callable[[CliContext], None] = lambda x: None
    """ Hook to run before running appy. """
    post_apply: Callable[[CliContext], None] = lambda x: None
    """ Hook to run after running appy. """

class ConfigureCliConfiguration(NamedTuple):
    hooks: Hooks = Hooks()
    """ Hooks to run before/after stages """
    settings_groups: List[ConfigSettingsGroup] = None
    """ Settings for building interactive configure prompt """


class Configuration(NamedTuple):
    """
    Configuration for building the CLI.
    """

    app_name: str
    """ Name of the application (do not use spaces). """

    docker_image: str
    """ The docker image used to run the CLI. """

    seed_app_configuration_file: Path
    """
    Path to a seed YAML file containing variables which are applied to the
    templates to generate the final configuration files.
    """

    seed_templates_dir: Path
    """
    Seed directory containing jinja2 templates used to generate the final
    configuration files.
    """

    configure_cli_customisation: ConfigureCliConfiguration
    """
    Configuration for the `configure` CLI command
    """

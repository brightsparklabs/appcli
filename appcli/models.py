#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

from subprocess import CompletedProcess
from typing import Callable, Dict, List, NamedTuple
from pathlib import Path


class CliContext(NamedTuple):
    """ Shared context from a run of the CLI. """

    configuration_dir: Path
    """ Directory to read configuration files from. """

    data_dir: Path
    """ Directory to store data to. """

    environment: str
    """ Environment to run. """

    subcommand_args: tuple
    """ Arguments passed to CLI subcommand. """

    generated_configuration_dir: Path
    """ Directory to store the generated configuration files to. """

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
    """ Whether to print debug logs. """

    commands: Dict
    """ Internal commands. """


class Hooks(NamedTuple):
    """ Hooks to run before/after stages """

    pre_start: Callable[[CliContext], None] = lambda x: None
    """ Optional. Hook function to run before running 'start'. """
    post_start: Callable[[CliContext, CompletedProcess], None] = lambda x, y: None
    """ Optional. Hook function to run after running 'start'. """
    pre_stop: Callable[[CliContext], None] = lambda x: None
    """ Optional. Hook function to run before running 'stop'. """
    post_stop: Callable[[CliContext, CompletedProcess], None] = lambda x, y: None
    """ Optional. Hook function to run after running 'stop'. """
    pre_configure_init: Callable[[CliContext], None] = lambda x: None
    """ Optional. Hook function to run before running 'configure init'. """
    post_configure_init: Callable[[CliContext], None] = lambda x: None
    """ Optional. Hook function to run after running 'configure init'. """
    pre_configure_apply: Callable[[CliContext], None] = lambda x: None
    """ Optional. Hook function to run before running 'configure apply'. """
    post_configure_apply: Callable[[CliContext], None] = lambda x: None
    """ Optional. Hook function to run after running 'configure apply'. """


class Configuration(NamedTuple):
    """ Configuration for building the CLI. """

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

    docker_compose_file: Path = "cli/docker-compose.yml"
    """ Optional. Path to the docker-compose.yml file specifying all services """

    docker_compose_override_files: List[Path] = []
    """
    Optional. Paths to the docker-compose.override.yml files specifying all services.
    These are applied in the supplied list order.
    """

    hooks: Hooks = Hooks()
    """ Optional. Hooks to run before/after stages. """

    custom_commands: List[Callable] = []
    """
    Optional. Extra click commands to add to the CLI. Can be group or specific commands.
    """

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
from pathlib import Path
from typing import Callable, Dict, FrozenSet, Iterable, NamedTuple, Tuple
from subprocess import CompletedProcess


class CliContext(NamedTuple):
    """ Shared context from a run of the CLI. """

    configuration_dir: Path
    """ Directory to read configuration files from. """

    data_dir: Path
    """ Directory to use for persistent data storage. """

    additional_data_dirs: Iterable[Tuple[str, Path]]
    """ Additional directories to use for persistent data storage. """

    key_file: Path
    """ File containing key for encryption/decryption. """

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

    additional_env_variables: Iterable[Tuple[str, str]]
    """ Additional environment variables to define in CLI container. """


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

    docker_compose_override_files: Iterable[Path] = []
    """
    Optional. Paths to the docker-compose.override.yml files specifying all services.
    These are applied in the supplied list order.
    """

    hooks: Hooks = Hooks()
    """ Optional. Hooks to run before/after stages. """

    custom_commands: Iterable[Callable] = []
    """
    Optional. Extra click commands to add to the CLI. Can be group or specific commands.
    """

    mandatory_additional_data_dirs: FrozenSet[Tuple[str, Path]] = frozenset()
    """
    Optional. Additional data directories which must be supplied.
    """

    mandatory_additional_env_variables: FrozenSet[Tuple[str, Path]] = frozenset()
    """
    Optional. Additional environment variables which must be supplied.
    """

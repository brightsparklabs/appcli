#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
from pathlib import Path
from typing import Dict, Iterable, NamedTuple, Tuple


class CliContext(NamedTuple):
    """ Shared context from a run of the CLI. """

    # ---------------------------------
    # data passed in when cli invoked on the command line
    # ---------------------------------

    configuration_dir: Path
    """ Directory to read configuration files from. """

    data_dir: Path
    """ Directory to use for persistent data storage. """

    additional_data_dirs: Iterable[Tuple[str, Path]]
    """ Additional directories to use for persistent data storage. """

    additional_env_variables: Iterable[Tuple[str, str]]
    """ Additional environment variables to define in CLI container. """

    environment: str
    """ Environment to run. """

    subcommand_args: tuple
    """ Arguments passed to CLI subcommand. """

    debug: bool
    """ Whether to print debug logs. """

    # ---------------------------------
    # derived data
    # ---------------------------------

    key_file: Path
    """ File containing key for encryption/decryption. """

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

    project_name: str
    """ Project name for launching docker containers/networks. """

    # ---------------------------------
    # cli build data
    # ---------------------------------

    app_version: str
    """ The application's version """

    commands: Dict
    """ Internal commands. """

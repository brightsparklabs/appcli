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

    def get_key_file(self) -> Path:
        return Path(self.configuration_dir, "key")

    def get_generated_configuration_dir(self) -> Path:
        return self.configuration_dir.joinpath(".generated")

    def get_app_configuration_file(self) -> Path:
        return self.configuration_dir.joinpath(f"{self.app_name.lower()}.yml")

    def get_templates_dir(self) -> Path:
        return self.configuration_dir.joinpath("templates")

    def get_project_name(self) -> str:
        return f"{self.app_name}_{self.environment}"

    # ---------------------------------
    # cli build data
    # ---------------------------------

    app_name: str
    """ The application's name """

    app_version: str
    """ The application's version """

    commands: Dict
    """ Internal commands. """

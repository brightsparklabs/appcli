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
    # cli build data
    # ---------------------------------

    app_name: str
    """ The application's name """

    app_version: str
    """ The application's version """

    commands: Dict
    """ Internal commands. """

    # ---------------------------------
    # derived data
    # ---------------------------------

    def get_key_file(self) -> Path:
        """Get the location of the key file for decrypting secrets

        Returns:
            Path: location of the key file
        """
        return Path(self.configuration_dir, "key")

    def get_generated_configuration_dir(self) -> Path:
        """Get the directory containing the generated configuration

        Returns:
            Path: directory of generated configuration
        """
        return self.configuration_dir.joinpath(".generated")

    def get_configuration_metadata_dir(self) -> Path:
        """Get the directory containing the metadata for app configuration

        Returns:
            Path: directory of application metadata
        """
        return self.configuration_dir.joinpath(".metadata")

    def get_app_configuration_file(self) -> Path:
        """Get the location of the configuration file

        Returns:
            Path: location of the configuration file
        """
        return self.configuration_dir.joinpath(f"settings.yml")

    def get_baseline_template_overrides_dir(self) -> Path:
        """Get the directory of the configuration template overrides

        Returns:
            Path: directory of configuration template overrides
        """
        return self.configuration_dir.joinpath("overrides")

    def get_configurable_templates_dir(self) -> Path:
        """Get the directory containing client-specific templates that aren't overrides,
        but that need to be applied separately.

        Returns:
            Path: directory of configurable templates
        """
        return self.configuration_dir.joinpath("templates")

    def get_project_name(self) -> str:
        """Get a unique name for the application and environment

        Returns:
            str: the project name
        """
        return f"{self.app_name}_{self.environment}"

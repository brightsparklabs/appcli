#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
from pathlib import Path
from typing import Dict, Iterable, NamedTuple, Tuple

# local libraries
from appcli.configuration.configuration_dir_state import (
    ConfigurationDirState,
    ConfigurationDirStateFactory,
)
from appcli.logger import logger


class CliContext(NamedTuple):
    """ Shared context from a run of the CLI. """

    # ---------------------------------
    # data passed in when CLI invoked on the command line
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

    docker_credentials_file: Path
    """ Path to the Docker credentials file (config.json) on the host for private docker registries. """

    subcommand_args: tuple
    """ Arguments passed to CLI subcommand. """

    debug: bool
    """ Whether to print debug logs. """

    # ---------------------------------
    # CLI build data
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

    def get_configuration_dir_state(self) -> ConfigurationDirState:
        """Gets the state of the configuration, for use in validating whether
        a command can be used or not.

        Returns:
            ConfigurationDirState: The state of the configuration.
        """
        configuration_dir_state: ConfigurationDirState = (
            ConfigurationDirStateFactory.get_state(
                self.configuration_dir,
                self.get_generated_configuration_dir(),
                self.app_version,
            )
        )
        logger.debug(f"Derived configuration state [{configuration_dir_state}]")
        return configuration_dir_state

    def get_key_file(self) -> Path:
        """Get the location of the key file for decrypting secrets

        Returns:
            Path: location of the key file
        """
        if self.configuration_dir is None:
            return None
        return Path(self.configuration_dir, "key")

    def get_generated_configuration_dir(self) -> Path:
        """Get the directory containing the generated configuration

        Returns:
            Path: directory of generated configuration
        """
        if self.configuration_dir is None:
            return None
        return self.configuration_dir.joinpath(".generated")

    def get_configuration_metadata_dir(self) -> Path:
        """Get the directory containing the metadata for app configuration

        Returns:
            Path: directory of application metadata
        """
        if self.configuration_dir is None:
            return None
        return self.configuration_dir.joinpath(".metadata")

    def get_app_configuration_file(self) -> Path:
        """Get the location of the configuration file

        Returns:
            Path: location of the configuration file
        """
        if self.configuration_dir is None:
            return None
        return self.configuration_dir.joinpath("settings.yml")

    def get_baseline_template_overrides_dir(self) -> Path:
        """Get the directory of the configuration template overrides

        Returns:
            Path: directory of configuration template overrides
        """
        if self.configuration_dir is None:
            return None
        return self.configuration_dir.joinpath("overrides")

    def get_configurable_templates_dir(self) -> Path:
        """Get the directory containing client-specific templates that
        aren't overrides,
        but that need to be applied separately.

        Returns:
            Path: directory of configurable templates
        """
        if self.configuration_dir is None:
            return None
        return self.configuration_dir.joinpath("templates")

    def get_project_name(self) -> str:
        """Get a unique name for the application and environment

        Returns:
            str: the project name
        """
        return f"{self.app_name}_{self.environment}"

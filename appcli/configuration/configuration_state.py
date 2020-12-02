#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
States of the configuration directory.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries

# vendor libraries

# local libraries
# from appcli.logger import logger

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


from pathlib import Path

from appcli.logger import logger
from appcli.commands.commands import AppcliCommand


class ConfigurationState:
    def __init__(self, cannot_run, cannot_run_unless_forced) -> None:
        self.cannot_run = cannot_run
        self.cannot_run_unless_forced = cannot_run_unless_forced

    def verify_command_allowed(self, command: AppcliCommand, force: bool = False):
        if command in self.cannot_run:
            logger.error(self.cannot_run[command])
            return False
        if command in self.cannot_run_unless_forced and not force:
            logger.error(self.cannot_run_unless_forced[command])
            return False
        return True


class ConfigurationStateFactory:
    def get_state(
        configuration_dir: Path, generated_configuration_path: Path
    ) -> ConfigurationState:
        if configuration_dir is None:
            return UninitialisedConfigurationState()
        # TODO: Impl all the states and logic to get those states
        return CleanConfigurationState()


class UninitialisedConfigurationState(ConfigurationState):
    """Represents the state where config directory doesn't exist yet."""

    def __init__(self) -> None:

        uninitialised_error_message = (
            "Cannot run command against uninitialised application."
        )

        # TODO: Determine commands
        cannot_run = {
            # AppcliCommand.CONFIGURE_INIT: uninitialised_error_message, # Initialises the conf dir
            AppcliCommand.CONFIGURE_APPLY: uninitialised_error_message,
            AppcliCommand.CONFIGURE_GET: uninitialised_error_message,
            AppcliCommand.CONFIGURE_SET: uninitialised_error_message,
            AppcliCommand.CONFIGURE_DIFF: uninitialised_error_message,
            AppcliCommand.CONFIGURE_EDIT: uninitialised_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_LS: uninitialised_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_GET: uninitialised_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_OVERRIDE: uninitialised_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_DIFF: uninitialised_error_message,
            AppcliCommand.DEBUG_INFO: uninitialised_error_message,
            AppcliCommand.ENCRYPT: uninitialised_error_message,
            # AppcliCommand.INSTALL: uninitialised_error_message, # Doesn't require conf dir
            # AppcliCommand.LAUNCHER: uninitialised_error_message, # Doesn't require conf dir
            AppcliCommand.MIGRATE: uninitialised_error_message,
            AppcliCommand.SERVICE_START: uninitialised_error_message,
            AppcliCommand.SERVICE_SHUTDOWN: uninitialised_error_message,
            AppcliCommand.SERVICE_LOGS: uninitialised_error_message,
            AppcliCommand.TASK_RUN: uninitialised_error_message,
            AppcliCommand.ORCHESTRATOR: uninitialised_error_message,
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class CleanConfigurationState(ConfigurationState):
    """Represents the state where config and generated directories both exist
    and are in a clean state.
    """

    def __init__(self) -> None:

        # TODO: Determine commands
        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise, already exists."
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class DirtyConfConfigurationState(ConfigurationState):
    """Represents the state where config directory is dirty."""

    def __init__(self) -> None:

        # TODO: Determine commands
        cannot_run = {}
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class DirtyGenConfigurationState(ConfigurationState):
    """Represents the state where generated directory is dirty."""

    def __init__(self) -> None:

        # TODO: Determine commands
        cannot_run = {}
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class DirtyConfAndGenConfigurationState(ConfigurationState):
    """Represents the state where both the conf and generated directory are dirty."""

    def __init__(self) -> None:

        # TODO: Determine commands
        cannot_run = {}
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class InvalidConfigurationState(ConfigurationState):
    """Represents the state where configuration is invalid and incompatible with appcli."""

    def __init__(self) -> None:

        # TODO: Determine commands
        cannot_run = {}
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)

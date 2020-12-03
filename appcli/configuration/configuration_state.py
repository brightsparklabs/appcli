#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
States of the configuration directory.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
# from appcli.functions import error_and_exit
from dataclasses import dataclass
from pathlib import Path

# vendor libraries

# local libraries
from appcli.logger import logger
from appcli.commands.commands import AppcliCommand

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigurationState:
    def __init__(self, cannot_run, cannot_run_unless_forced) -> None:
        self.cannot_run = cannot_run
        self.cannot_run_unless_forced = cannot_run_unless_forced

    def verify_command_allowed(self, command: AppcliCommand, force: bool = False):
        if command in self.cannot_run:
            # TODO: Use error_and_exit once circular dep is gone
            # error_and_exit(self.cannot_run[command])
            logger.error(self.cannot_run[command])
            raise SystemExit(1) from SystemExit(self.cannot_run[command])
        if command in self.cannot_run_unless_forced and not force:
            # TODO: Use error_and_exit once circular dep is gone
            # error_and_exit(self.cannot_run_unless_forced[command])
            logger.error(
                f"{self.cannot_run_unless_forced[command]} If this command supports it, use '--force' to ignore error."
            )
            raise SystemExit(1) from SystemExit(self.cannot_run_unless_forced[command])
        # TODO: swap to debug message
        logger.error(
            f"Allowed command [{command}] with current state [{self}], where force is [{force}]."
        )


class ConfigurationStateFactory:
    def get_state(
        configuration_dir: Path, generated_configuration_path: Path
    ) -> ConfigurationState:
        if configuration_dir is None:
            return NoDirectoryProvidedConfigurationState()
        # TODO: Impl all the states and logic to get those states
        return AllowAllConfigurationState()
        # return CleanConfigurationState()

        # pre-apply:
        #   confirm_not_on_master_branch,
        #   confirm_config_version_matches_app_version,
        # pre-migrate:
        #   confirm_generated_configuration_is_using_current_configuration
        #   - check this by the metadata file...
        # pre-start:
        #   confirm_config_version_matches_app_version


class AllowAllConfigurationState(ConfigurationState):
    """TESTING. REMOVE."""

    def __init__(self) -> None:

        cannot_run = {}
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class NoDirectoryProvidedConfigurationState(ConfigurationState):
    """Represents the state where appcli doesn't know the path to configuration dir."""

    def __init__(self) -> None:

        default_error_message = (
            "No configuration directory provided to appcli. Run 'install'."
        )

        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: default_error_message,
            AppcliCommand.CONFIGURE_APPLY: default_error_message,
            AppcliCommand.CONFIGURE_GET: default_error_message,
            AppcliCommand.CONFIGURE_SET: default_error_message,
            AppcliCommand.CONFIGURE_DIFF: default_error_message,
            AppcliCommand.CONFIGURE_EDIT: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_LS: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_GET: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_OVERRIDE: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_DIFF: default_error_message,
            AppcliCommand.DEBUG_INFO: default_error_message,
            AppcliCommand.ENCRYPT: default_error_message,
            AppcliCommand.LAUNCHER: default_error_message,
            AppcliCommand.MIGRATE: default_error_message,
            AppcliCommand.SERVICE_START: default_error_message,
            AppcliCommand.SERVICE_SHUTDOWN: default_error_message,
            AppcliCommand.SERVICE_LOGS: default_error_message,
            AppcliCommand.TASK_RUN: default_error_message,
            AppcliCommand.ORCHESTRATOR: default_error_message,
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class UninitialisedConfigurationState(ConfigurationState):
    """Represents the state where config directory hasn't been initialised."""

    def __init__(self) -> None:

        default_error_message = "Cannot run command against uninitialised application. Run 'configure init'."

        cannot_run = {
            AppcliCommand.CONFIGURE_APPLY: default_error_message,
            AppcliCommand.CONFIGURE_GET: default_error_message,
            AppcliCommand.CONFIGURE_SET: default_error_message,
            AppcliCommand.CONFIGURE_DIFF: default_error_message,
            AppcliCommand.CONFIGURE_EDIT: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_LS: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_GET: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_OVERRIDE: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_DIFF: default_error_message,
            AppcliCommand.DEBUG_INFO: default_error_message,
            AppcliCommand.ENCRYPT: default_error_message,
            AppcliCommand.INSTALL: default_error_message,
            AppcliCommand.MIGRATE: default_error_message,
            AppcliCommand.SERVICE_START: default_error_message,
            AppcliCommand.SERVICE_SHUTDOWN: default_error_message,
            AppcliCommand.SERVICE_LOGS: default_error_message,
            AppcliCommand.TASK_RUN: default_error_message,
            AppcliCommand.ORCHESTRATOR: default_error_message,
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class CleanConfigurationState(ConfigurationState):
    """Represents the state where config and generated directories both exist
    and are in a clean state.
    """

    def __init__(self) -> None:
        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.INSTALL: "Cannot install over the top of existing application.",
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class DirtyConfConfigurationState(ConfigurationState):
    """Represents the state where config directory is dirty."""

    def __init__(self) -> None:

        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.INSTALL: "Cannot install over the top of existing application.",
            AppcliCommand.MIGRATE: "Cannot migrate with a dirty configuration. Run 'configure apply'.",
        }
        cannot_run_unless_forced = {
            AppcliCommand.SERVICE_START: "Cannot start with dirty configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run task with dirty configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator tasks with dirty configuration. Run 'configure apply'.",
        }

        super().__init__(cannot_run, cannot_run_unless_forced)


class DirtyGenConfigurationState(ConfigurationState):
    """Represents the state where generated directory is dirty."""

    def __init__(self) -> None:

        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.INSTALL: "Cannot install over the top of existing application.",
            AppcliCommand.MIGRATE: "Cannot migrate with a dirty generated configuration. Run 'configure apply'.",
        }
        cannot_run_unless_forced = {
            AppcliCommand.CONFIGURE_APPLY: "Cannot 'configure apply' over a dirty generated directory as it will overwrite existing modifications.",
            AppcliCommand.SERVICE_START: "Cannot start service with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run task with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator tasks with dirty generated configuration. Run 'configure apply'.",
        }

        super().__init__(cannot_run, cannot_run_unless_forced)


class DirtyConfAndGenConfigurationState(ConfigurationState):
    """Represents the state where both the conf and generated directory are dirty."""

    def __init__(self) -> None:

        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.INSTALL: "Cannot install over the top of existing application.",
            AppcliCommand.MIGRATE: "Cannot migrate with a dirty generated configuration. Run 'configure apply'.",
        }
        cannot_run_unless_forced = {
            AppcliCommand.CONFIGURE_APPLY: "Cannot 'configure apply' over a dirty generated directory as it will overwrite existing modifications.",
            AppcliCommand.SERVICE_START: "Cannot start service with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run task with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator tasks with dirty generated configuration. Run 'configure apply'.",
        }

        super().__init__(cannot_run, cannot_run_unless_forced)


class InvalidConfigurationState(ConfigurationState):
    """Represents the state where configuration is invalid and incompatible with appcli."""

    def __init__(self) -> None:

        default_error_message = "Invalid configuration state."

        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: default_error_message,
            AppcliCommand.CONFIGURE_APPLY: default_error_message,
            AppcliCommand.CONFIGURE_GET: default_error_message,
            AppcliCommand.CONFIGURE_SET: default_error_message,
            AppcliCommand.CONFIGURE_DIFF: default_error_message,
            AppcliCommand.CONFIGURE_EDIT: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_LS: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_GET: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_OVERRIDE: default_error_message,
            AppcliCommand.CONFIGURE_TEMPLATE_DIFF: default_error_message,
            AppcliCommand.DEBUG_INFO: default_error_message,
            AppcliCommand.ENCRYPT: default_error_message,
            AppcliCommand.INSTALL: default_error_message,
            AppcliCommand.LAUNCHER: default_error_message,
            AppcliCommand.MIGRATE: default_error_message,
            AppcliCommand.SERVICE_START: default_error_message,
            AppcliCommand.SERVICE_SHUTDOWN: default_error_message,
            AppcliCommand.SERVICE_LOGS: default_error_message,
            AppcliCommand.TASK_RUN: default_error_message,
            AppcliCommand.ORCHESTRATOR: default_error_message,
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)

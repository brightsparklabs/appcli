#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
States that the configuration directory can be in.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from pathlib import Path

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.functions import error_and_exit
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
)
from appcli.logger import logger

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigurationDirState:
    """The state of the configuration directory.

    This is the base class from which all the different 'state' classes of the
    configuration directory will inherit.

    e.g. The 'state' class representing the configuration directory is
    CleanConfigurationDirState.
    """

    def __init__(self, cannot_run, cannot_run_unless_forced) -> None:
        self.cannot_run = cannot_run
        self.cannot_run_unless_forced = cannot_run_unless_forced

    def verify_command_allowed(self, command: AppcliCommand, force: bool = False):
        if command in self.cannot_run:
            error_and_exit(self.cannot_run[command])
        if command in self.cannot_run_unless_forced and not force:
            error_and_exit(
                f"{self.cannot_run_unless_forced[command]}"
                " If this command supports it, use '--force' to ignore error."
            )
        logger.debug(
            f"Allowed command [{command}] with current configuration state [{self}], where force is [{force}]."
        )


class ConfigurationDirStateFactory:
    def get_state(
        configuration_dir: Path, generated_configuration_dir: Path, app_version: str
    ) -> ConfigurationDirState:
        if configuration_dir is None:
            return NoDirectoryProvidedConfigurationDirState()

        config_repo = ConfigurationGitRepository(configuration_dir)
        gen_config_repo = GeneratedConfigurationGitRepository(
            generated_configuration_dir
        )

        if not config_repo.repo_exists():
            return UninitialisedConfigurationDirState()

        conf_version = config_repo.get_repository_version()
        if conf_version != app_version:
            error_message = f"Application requires migration. Configuration version [{conf_version}], Application version [{app_version}]."
            return InvalidConfigurationDirState(error_message)

        if not gen_config_repo.repo_exists():
            return UnappliedConfigurationDirState()

        if config_repo.is_dirty():
            if gen_config_repo.is_dirty():
                return DirtyConfAndGenConfigurationDirState()
            return DirtyConfConfigurationDirState()

        if gen_config_repo.is_dirty():
            return DirtyGenConfigurationDirState()

        if gen_config_repo.get_commit_count() > 1:
            return InvalidConfigurationDirState(
                f"Generated repository [{gen_config_repo.get_repo_path()}] has extra untracked git commits."
            )

        return CleanConfigurationDirState()


class NoDirectoryProvidedConfigurationDirState(ConfigurationDirState):
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


class UninitialisedConfigurationDirState(ConfigurationDirState):
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


class UnappliedConfigurationDirState(ConfigurationDirState):
    """Represents the state where configuration hasn't been applied yet, i.e. the generated configuration doesn't exist."""

    def __init__(self) -> None:

        cannot_run = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.INSTALL: "Cannot install over the top of existing application.",
            AppcliCommand.SERVICE_START: "Cannot start services due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.SERVICE_SHUTDOWN: "Cannot stop services due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.SERVICE_LOGS: "Cannot get service logs due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run tasks due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator commands due to missing generated configuration. Run 'configure apply'.",
        }
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)


class CleanConfigurationDirState(ConfigurationDirState):
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


class DirtyConfConfigurationDirState(ConfigurationDirState):
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


class DirtyGenConfigurationDirState(ConfigurationDirState):
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


class DirtyConfAndGenConfigurationDirState(ConfigurationDirState):
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


class InvalidConfigurationDirState(ConfigurationDirState):
    """Represents the state where configuration is invalid and incompatible with appcli."""

    def __init__(self, error: str) -> None:

        default_error_message = f"Invalid configuration state, this error must be rectified before continuing. {error}"

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

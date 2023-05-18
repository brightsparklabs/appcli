#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
States that the configuration directory can be in.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from collections import defaultdict
from pathlib import Path
from typing import Iterable

# vendor libraries
import git

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
    """The state of the configuration directory. This encapsulates both the 'conf' and 'generated' git-managed
    directories.

    This is the base class from which all the different 'state' classes of the configuration directory will inherit.
    """

    def __init__(self, disallowed_command, disallowed_command_unless_forced) -> None:
        self.disallowed_command = disallowed_command
        self.disallowed_command_unless_forced = disallowed_command_unless_forced

    def verify_command_allowed(self, command: AppcliCommand, force: bool = False):
        if command in self.disallowed_command:
            error_and_exit(self.disallowed_command[command])
        if command in self.disallowed_command_unless_forced and not force:
            error_and_exit(
                f"{self.disallowed_command_unless_forced[command]}"
                " If this command supports it, use '--force' to ignore error."
            )
        logger.debug(
            f"Allowed command [{command}] with current configuration state [{self.__class__.__name__}], where force is [{force}]."
        )


class ConfigurationDirStateFactory:
    """Factory class to get the current ConfigurationDirState state class"""

    def get_state(
        configuration_dir: Path,
        generated_configuration_dir: Path,
        app_version: str,
        backup_dir: Path,
    ) -> ConfigurationDirState:
        if configuration_dir is None:
            return NoDirectoryProvidedConfigurationDirState()

        if backup_dir is None:
            return NoDirectoryProvidedBackupDirState()

        if not backup_dir.exists():
            return BackupDirectoryDoesNotExist()

        if not ConfigurationDirStateFactory.__is_git_repo(configuration_dir):
            return UninitialisedConfigurationDirState()

        config_repo = ConfigurationGitRepository(configuration_dir)

        conf_version = config_repo.get_repository_version()
        if conf_version != app_version:
            error_message = f"Application requires migration. Configuration version [{conf_version}], Application version [{app_version}]."
            return RequiresMigrationConfigurationDirState(error_message)

        if not ConfigurationDirStateFactory.__is_git_repo(generated_configuration_dir):
            return UnappliedConfigurationDirState()
        gen_config_repo = GeneratedConfigurationGitRepository(
            generated_configuration_dir
        )

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

    def __is_git_repo(path: Path):
        """Checks if the directory at the path is a git repository.

        Args:
            path (Path): Path to test.

        Returns:
            bool: True if the directory exists and is a git repo. Otherwise False.
        """
        try:
            # If this doesn't raise an Exception, a git repo exists at this path.
            git.Repo(path)
            return True
        except (git.InvalidGitRepositoryError, git.exc.NoSuchPathError):
            return False


class NoDirectoryProvidedConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where appcli doesn't know the path to configuration dir."""

    def __init__(self) -> None:
        default_error_message = (
            "No configuration directory provided to appcli. Run 'install'."
        )

        disallowed_command = get_disallowed_command_from_allowed_commands(
            [AppcliCommand.INSTALL],
            default_error_message,
        )
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class NoDirectoryProvidedBackupDirState(ConfigurationDirState):
    """Represents the backup dir state where appcli doesn't know the path to backup dir."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.BACKUP: "Cannot backup due to missing backup directory. Run 'install'.",
            AppcliCommand.RESTORE: "Cannot restore due to missing backup directory. Run 'install'.",
            AppcliCommand.VIEW_BACKUPS: "Cannot view backups due to missing backup directory. Run 'install'.",
        }
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class BackupDirectoryDoesNotExist(ConfigurationDirState):
    """Represents the backup dir state where the backup directory does not exist."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.RESTORE: "Cannot restore due to missing backup directory. Run 'backup'.",
            AppcliCommand.VIEW_BACKUPS: "Cannot view backups due to missing backup directory. Run 'backup'.",
        }
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class UninitialisedConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where config directory hasn't been initialised."""

    def __init__(self) -> None:
        default_error_message = "Cannot run command against uninitialised application. Run 'configure init'."

        disallowed_command = get_disallowed_command_from_allowed_commands(
            [
                AppcliCommand.CONFIGURE_INIT,
                AppcliCommand.LAUNCHER,
                AppcliCommand.BACKUP,
                AppcliCommand.RESTORE,
                AppcliCommand.VIEW_BACKUPS,
            ],
            default_error_message,
        )
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class UnappliedConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where configuration hasn't been applied yet, i.e. the generated
    configuration doesn't exist."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.SERVICE_START: "Cannot start services due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.SERVICE_SHUTDOWN: "Cannot stop services due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.SERVICE_LOGS: "Cannot get service logs due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.SERVICE_STATUS: "Cannot get the status of services due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run tasks due to missing generated configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator commands due to missing generated configuration. Run 'configure apply'.",
        }
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class CleanConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where config and generated directories both exist and are in a clean
    state."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
        }
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class DirtyConfConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where config directory is dirty."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.MIGRATE: "Cannot migrate with a dirty configuration. Run 'configure apply'.",
        }
        disallowed_command_unless_forced = {
            AppcliCommand.SERVICE_START: "Cannot start with dirty configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run task with dirty configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator tasks with dirty configuration. Run 'configure apply'.",
        }

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class DirtyGenConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where generated directory is dirty."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.MIGRATE: "Cannot migrate with a dirty generated configuration. Run 'configure apply'.",
        }
        disallowed_command_unless_forced = {
            AppcliCommand.CONFIGURE_APPLY: "Cannot 'configure apply' over a dirty generated directory as it will overwrite existing modifications.",
            AppcliCommand.SERVICE_START: "Cannot start service with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run task with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator tasks with dirty generated configuration. Run 'configure apply'.",
        }

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class DirtyConfAndGenConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where both the conf and generated directory are dirty."""

    def __init__(self) -> None:
        disallowed_command = {
            AppcliCommand.CONFIGURE_INIT: "Cannot initialise an existing configuration.",
            AppcliCommand.MIGRATE: "Cannot migrate with a dirty generated configuration. Run 'configure apply'.",
        }
        disallowed_command_unless_forced = {
            AppcliCommand.CONFIGURE_APPLY: "Cannot 'configure apply' over a dirty generated directory as it will overwrite existing modifications.",
            AppcliCommand.SERVICE_START: "Cannot start service with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.TASK_RUN: "Cannot run task with dirty generated configuration. Run 'configure apply'.",
            AppcliCommand.ORCHESTRATOR: "Cannot run orchestrator tasks with dirty generated configuration. Run 'configure apply'.",
        }

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class RequiresMigrationConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where configuration and application versions are misaligned."""

    def __init__(self, error: str) -> None:
        disallowed_command = get_disallowed_command_from_allowed_commands(
            [AppcliCommand.MIGRATE], error
        )
        disallowed_command_unless_forced = {}

        super().__init__(disallowed_command, disallowed_command_unless_forced)


class InvalidConfigurationDirState(ConfigurationDirState):
    """Represents the configuration dir state where configuration is invalid and incompatible with appcli."""

    def __init__(self, error: str) -> None:
        default_error_message = f"Invalid configuration state, this error must be rectified before continuing. {error}"

        # Remove the 'VIEW_BACKUPS' and 'RESTORE' commands from the set of 'disallowed' commands so that we can add them
        # as 'disallowed unless forced' commands
        disallowed_command = get_disallowed_command_from_allowed_commands(
            [AppcliCommand.VIEW_BACKUPS, AppcliCommand.RESTORE], default_error_message
        )
        disallowed_command_unless_forced = {
            AppcliCommand.VIEW_BACKUPS: default_error_message,
            AppcliCommand.RESTORE: default_error_message,
        }
        super().__init__(disallowed_command, disallowed_command_unless_forced)


def get_disallowed_command_from_allowed_commands(
    allowed_commands: Iterable[AppcliCommand], error_message: str
) -> dict:
    """Given an Iterable of allowed appcli commands, generates the dict of disallowed commands.

    Args:
        allowed_commands (Iterable[AppcliCommand]): Allowed commands.
        error_message (str): Error message for disallowed commands.

    Returns:
        dict: [description]
    """

    disallowed_commands = dict(defaultdict.fromkeys(list(AppcliCommand), error_message))

    for command in allowed_commands:
        disallowed_commands.pop(command, None)

    return disallowed_commands

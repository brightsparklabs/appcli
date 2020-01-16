#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles git repositories for configuration directories for appcli
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import json
import os
from pathlib import Path
from typing import Iterable

# vendor libraries
import git

# local libraries
from appcli.functions import get_generated_configuration_metadata_file
from appcli.logger import logger
from appcli.models.cli_context import CliContext

# ------------------------------------------------------------------------------
# PRIVATE CLASSES
# ------------------------------------------------------------------------------


class GitRepository:
    """Class which encapsulates different git repo actions for configuration repositories
    """

    def __init__(self, repo_path: str, ignores: Iterable[str] = None):
        self.repo_path = repo_path
        self.ignores = ignores
        self.actor: git.Actor = git.Actor(f"appcli", "root@localhost")

    def init(self):
        """Initialise the git repository, create .gitignore if required, and commit the initial files
        """
        logger.info("Initialising repository at [%s] ...", self.repo_path)

        # Confirm that a repo doesn't already exist at this directory
        if self.repo_exists():
            raise Exception(
                f"Cannot initialise repo at [{self.repo_path}], already exists."
            )

        # git init, and write to the .gitignore file
        repo = git.Repo.init(self.repo_path)
        logger.debug("Initialised repository at [%s]", repo.working_dir)
        if self.ignores:
            with open(self.repo_path.joinpath(".gitignore"), "w+") as ignore_file:
                for ignore in self.ignores:
                    ignore_file.write(f"{ignore}\n")
            logger.debug("Created .gitignore with ignores: %s", self.ignores)
            repo.index.add(".gitignore")

        # do the initial commit on the repo
        repo.index.add("*")
        repo.index.commit("[autocommit] Initialised repository", author=self.actor)
        logger.debug("Committed repository at [%s]", repo.working_dir)

    def commit_changes(self, message: str):
        """Commit the existing changes to the git repository

        Args:
            message (str): The commit message to use

        """
        repo = self._get_repo()

        # If the repo isn't dirty, don't commit
        if not repo.is_dirty(untracked_files=True):
            logger.info(
                "No changes found in repository [%s], no commit was made.",
                repo.working_dir,
            )
            return

        # Add all files (and optionally the .gitignore if it exists)
        if Path(repo.working_dir).joinpath(".gitignore").exists():
            repo.index.add(".gitignore")
        repo.index.add("*")

        repo.index.commit(message, author=self.actor)

    def is_dirty(self, untracked_files: bool = False):
        """Tests if the repository is dirty or not. True if dirty, False if not.

        Args:
            untracked_files (bool, optional): Whether the check includes untracked files. Defaults to False.

        Returns:
            [bool]: True if repository is considered dirty, False otherwise.
        """
        repo = self._get_repo()

        return repo.is_dirty(untracked_files=untracked_files)

    def repo_exists(self):
        """Tests if the underlying repository has been initialised.

        Returns:
            [bool]: return True if the repository has been initialised, otherwise False.
        """
        try:
            git.Repo(self.repo_path)
            return True
        except Exception:
            return False

    def get_current_commit_hash(self):
        """Get the commit hash of the current commit
        """
        repo = self._get_repo()
        return repo.head.object.hexsha

    def _get_repo(self):
        """Get the repository if it exists, otherwise raise a custom Exception
        """
        try:
            repo = git.Repo(self.repo_path)
        except Exception:
            raise Exception(f"Configuration repository not found at [{self.repo_path}]")

        return repo


# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.configuration_dir, [".generated*"])


class GeneratedConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.get_generated_configuration_dir())


# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


def confirm_config_dir_exists(cli_context: CliContext):
    """Confirm that the configuration repository exists.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository does *not* exist.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if not config_repo.repo_exists():
        raise Exception(
            f"Configuration does not exist at [{config_repo.repo_path}]. Please run `configure init`."
        )


def confirm_config_dir_not_exists(cli_context: CliContext):
    """Confirm that the configuration repository does *not* exist.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository exists.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if config_repo.repo_exists():
        raise Exception(f"Configuration already exists at [{config_repo.repo_path}].")


def confirm_generated_config_dir_exists(cli_context: CliContext):
    """Confirm that the generated configuration repository exists.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the generated configuration repository does not exist.
    """
    generated_config_repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
        cli_context
    )
    if not generated_config_repo.repo_exists():
        raise Exception(
            f"Generated configuration does not exist at [{generated_config_repo.repo_path}]. Please run `configure apply`."
        )


def confirm_config_dir_is_not_dirty(cli_context: CliContext):
    """Confirm that the configuration repository has not been modified and not 'applied'.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository has been modified and not 'applied'.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if config_repo.is_dirty(untracked_files=True):
        raise Exception(
            f"Configuration at [{config_repo.repo_path}]] contains changes which have not been applied. Please run `configure apply`."
        )


def confirm_generated_config_dir_is_not_dirty(cli_context: CliContext):
    """Confirm that the generated configuration repository has not been manually modified and not checked-in.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the generated configuration repository has been manually modified and not checked in.
    """
    generated_config_repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
        cli_context
    )
    if generated_config_repo.is_dirty(untracked_files=False):
        raise Exception(
            f"Generated configuration at [{generated_config_repo.repo_path}] has been manually modified."
        )


def confirm_generated_configuration_is_using_current_configuration(
    cli_context: CliContext,
):
    """Confirm that the generated configuration directory was generated from the current state configuration directory.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if metadata file not found, or generated config is out of sync with config.
    """
    metadata_file = get_generated_configuration_metadata_file(cli_context)
    if not os.path.isfile(metadata_file):
        raise Exception(
            f"Could not find a metadata file at [{metadata_file}]. Please run `configure apply`"
        )

    with open(metadata_file, "r") as f:
        metadata = json.load(f)
        logger.debug("Metadata from generated configuration: %s", metadata)

    generated_commit_hash = metadata["generated_from_commit"]
    configuration_commit_hash = ConfigurationGitRepository(
        cli_context
    ).get_current_commit_hash()
    if generated_commit_hash != configuration_commit_hash:
        logger.debug(
            "Generated configuration hash [%s] does not match configuration hash [%s]",
            generated_commit_hash,
            configuration_commit_hash,
        )
        raise Exception(
            "Generated configuration is out of sync with raw configuration. Please run `configure apply`."
        )

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles git repositories for configuration directories for appcli
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
from pathlib import Path
from typing import Iterable

# vendor libraries
import git

# local libraries
from appcli.logger import logger
from appcli.models.cli_context import CliContext

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

BASE_BRANCH_NAME: str = "master"

# ------------------------------------------------------------------------------
# PUBLIC CLASSES
# ------------------------------------------------------------------------------


class GitRepository:
    """Class which encapsulates different git repo actions for configuration repositories"""

    def __init__(self, repo_path: Path, ignores: Iterable[str] = []):
        self.actor: git.Actor = git.Actor("appcli", "root@localhost")

        # Get or create repo at this path to ensure it exists
        try:
            repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            repo = self.__initialise_new_repo(repo_path, ignores)

        self.repo = repo

    def commit_changes(self, message: str) -> bool:
        """Commit the existing changes to the git repository

        Args:
            message (str): The commit message to use

        Returns:
            bool: True if a commit was made, otherwise False.

        """
        # If the repo isn't dirty, don't commit
        if not self.repo.is_dirty(untracked_files=True):
            logger.debug(
                "No changes found in repository [%s], no commit was made.",
                self.repo.working_dir,
            )
            return False

        logger.debug(
            "Changes found in repository [%s], making new commit.",
            self.repo.working_dir,
        )

        self.repo.git.add(".gitignore")
        self.repo.git.add("*")
        self.repo.index.commit(message, author=self.actor)
        return True

    def checkout_new_branch_from_master(self, branch_name: str):
        """Checkout a new branch from the HEAD of master

        Args:
            branch_name (str): name of the new branch
        """
        self.checkout_existing_branch("master")
        self.repo.git.checkout("HEAD", b=branch_name)

    def checkout_existing_branch(self, branch_name: str):
        """Checkout an existing branch

        Args:
            branch_name (str): name of the branch to checkout to
        """
        self.repo.git.checkout(branch_name)

    def get_repository_version(self) -> str:
        """Get the nominal 'version' associated with this git repository. This is not a 'git'
        concept, but rather an 'appcli' concept for what 'version' the repository is using.

        Returns:
            str: the 'appcli-specific' version of this particular git repository, which aligns
                with the version of the application.
        """
        # Version is stored as a tag on the current branch
        return self.__get_current_branch_last_tag()

    def does_branch_exist(self, branch_name: str) -> bool:
        """Checks if a branch with a particular name exists

        Args:
            branch_name (str): the name of the branch to check

        Returns:
            bool: True if the branch exists, otherwise false
        """
        try:
            self.repo.git.show_ref(f"refs/heads/{branch_name}", verify=True, quiet=True)
            return True
        except Exception:
            return False

    def tag_current_commit(self, tag_name: str):
        """Tag the current commit with a tag name

        Args:
            tag_name (str): the tagname to use in the tag
        """
        self.repo.git.tag(tag_name)

    def is_dirty(self, untracked_files: bool = False):
        """Tests if the repository is dirty or not. True if dirty, False if not.

        Args:
            untracked_files (bool, optional): Whether the check includes untracked files. Defaults to False.

        Returns:
            [bool]: True if repository is considered dirty, False otherwise.
        """
        return self.repo.is_dirty(untracked_files=untracked_files)

    def get_current_commit_hash(self):
        """Get the commit hash of the current commit"""
        return self.repo.git.rev_parse("HEAD")

    def get_diff_to_tag(self, tag: str, diff_dir: str = ""):
        return self.repo.git.diff(f"tags/{tag}", f"{diff_dir}")

    def rename_current_branch(self, branch_name: str):
        """Renames the current branch

        Args:
            branch_name (str): the new branch name
        """
        self.repo.git.branch(m=branch_name)
        logger.debug(f"Renamed branch to [{branch_name}]")

    def __get_current_branch_name(self) -> str:
        """Get the name of the current branch

        Returns:
            str: name of the current branch
        """
        return self.repo.git.symbolic_ref("HEAD", short=True).replace("heads/", "")

    def __get_current_branch_last_tag(self) -> str:
        """Get the last tag for the current branch

        returns:
            str: version of the current branch
        """

        return self.repo.git.describe(tags=True, abbrev=0, always=True)

    def __initialise_new_repo(
        self, repo_path: Path, ignores: Iterable[str]
    ) -> git.Repo:
        # Initialise the git repository, create .gitignore if required, and commit the initial files
        logger.debug("Initialising repository at [%s] ...", repo_path)

        # git init, and write to the .gitignore file
        repo = git.Repo.init(repo_path)
        logger.debug("Initialised repository at [%s]", repo.working_dir)

        gitignore_path = repo_path.joinpath(".gitignore")
        with open(gitignore_path, "w") as ignore_file:
            for ignore in ignores:
                ignore_file.write(f"{ignore}\n")
        logger.debug(
            f"Created .gitignore at [{gitignore_path}] with ignores: [%s]", ignores
        )

        repo.git.add(".gitignore")
        repo.git.add("*")
        repo.index.commit("[autocommit] Initialised repository", author=self.actor)
        return repo


class ConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(
            cli_context.configuration_dir,
            [".generated*", ".metadata*"],
        )


class GeneratedConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.get_generated_configuration_dir())
        self.rename_current_branch(cli_context.app_conf_branch)


# ------------------------------------------------------------------------------
# PUBLIC FUNCTIONS
# ------------------------------------------------------------------------------


def confirm_config_dir_exists(cli_context: CliContext):
    """Confirm that the configuration repository exists.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository does *not* exist.
    """
    if not __is_git_repo(cli_context.configuration_dir):
        raise Exception(
            f"Configuration does not exist at [{cli_context.configuration_dir}]. Please run `configure init`."
        )


def confirm_config_dir_not_exists(cli_context: CliContext):
    """Confirm that the configuration repository does *not* exist.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository exists.
    """
    if __is_git_repo(cli_context.configuration_dir):
        raise Exception(
            f"Configuration already exists at [{cli_context.configuration_dir}]."
        )


def confirm_generated_config_dir_exists(cli_context: CliContext):
    """Confirm that the generated configuration repository exists.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the generated configuration repository does not exist.
    """
    if not __is_git_repo(cli_context.get_generated_configuration_dir()):
        raise Exception(
            f"Generated configuration does not exist at [{cli_context.get_generated_configuration_dir()}]. Please run `configure apply`."
        )


def confirm_config_dir_exists_and_is_not_dirty(cli_context: CliContext):
    """Confirm that the configuration repository has not been modified and not 'applied'.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository has been modified and not 'applied'.
    """
    confirm_config_dir_exists(cli_context)
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if config_repo.is_dirty(untracked_files=True):
        raise Exception(
            f"Configuration at [{config_repo.repo.working_dir}]] contains changes which have not been applied. Please run `configure apply`."
        )


def confirm_generated_config_dir_exists_and_is_not_dirty(cli_context: CliContext):
    """Confirm that the generated configuration repository has not been manually modified and not checked-in.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the generated configuration repository has been manually modified and not checked in.
    """
    confirm_generated_config_dir_exists(cli_context)
    generated_config_repo: GeneratedConfigurationGitRepository = (
        GeneratedConfigurationGitRepository(cli_context)
    )
    if generated_config_repo.is_dirty(untracked_files=False):
        raise Exception(
            f"Generated configuration at [{generated_config_repo.repo.working_dir}] has been manually modified."
        )


def confirm_config_version_matches_app_version(cli_context: CliContext):
    """Confirm that the configuration repository version matches the application version.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository version doesn't match the application version.
    """
    confirm_config_dir_exists(cli_context)
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    config_version: str = config_repo.get_repository_version()

    app_version: str = cli_context.app_version

    if config_version != app_version:
        raise Exception(
            f"Configuration at [{config_repo.repo.working_dir}] is using version [{config_version}] which is incompatible with current application version [{app_version}]. Migrate to this application version using 'migrate'."
        )


def confirm_not_on_master_branch(cli_context: CliContext):
    """Confirm that the configuration repository is not currently on the master branch.

    Args:
        cli_context (CliContext): the current cli context
    """
    confirm_config_dir_exists(cli_context)
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    config_version: str = config_repo.get_repository_version()

    if config_version == "master":
        raise Exception(
            f"Configuration at [{config_repo.repo.working_dir}] is on the master branch."
        )


# ------------------------------------------------------------------------------
# PRIVATE FUNCTIONS
# ------------------------------------------------------------------------------


def __is_git_repo(path: Path) -> bool:
    """Checks if a given path contains a git repo or not

    Args:
        path (Path): the path to test

    Returns:
        bool: True if this path contains a git repo at it's base, otherwise False.
    """
    try:
        git.Repo(path=path)
    except git.InvalidGitRepositoryError:
        return False
    else:
        return True

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
    """Class which encapsulates different git repo actions for configuration repositories
    """

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
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

    def set_gitignore(self, ignores: Iterable[str]):
        # Overwrite existing .gitignore file
        with open(self.repo_path.joinpath(".gitignore"), "w") as ignore_file:
            for ignore in ignores:
                ignore_file.write(f"{ignore}\n")
        logger.debug("Created .gitignore with ignores: [%s]", ignores)

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
            repo.git.add(".gitignore")
        repo.git.add("*")

        repo.index.commit(message, author=self.actor)

    def checkout_new_branch(self, branch_name: str):
        """Checkout a new branch from the current commit

        Args:
            branch_name (str): name of the new branch
        """
        repo = self._get_repo()
        repo.git.checkout("HEAD", b=branch_name)

    def checkout_existing_branch(self, branch_name: str):
        """Checkout an existing branch

        Args:
            branch_name (str): name of the branch to checkout to
        """
        repo = self._get_repo()
        repo.git.checkout(branch_name)

    def checkout_master_branch(self):
        """Checkout the 'master' branch
        """
        self.checkout_existing_branch("master")

    def get_current_branch_name(self) -> str:
        """Get the name of the current branch

        Returns:
            str: name of the current branch
        """
        repo = self._get_repo()
        return repo.git.symbolic_ref("HEAD", short=True)

    def does_branch_exist(self, branch_name: str) -> bool:
        """Checks if a branch with a particular name exists

        Args:
            branch_name (str): the name of the branch to check

        Returns:
            bool: True if the branch exists, otherwise false
        """
        repo = self._get_repo()
        try:
            repo.git.show_ref(f"refs/heads/{branch_name}", verify=True, quiet=True)
            return True
        except Exception:
            return False

    def tag_current_commit(self, tag_name: str):
        """Tag the current commit with a tag name

        Args:
            tag_name (str): the tagname to use in the tag
        """
        repo = self._get_repo()
        repo.git.tag(tag_name)

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
        return repo.git.rev_parse("HEAD")

    def _get_repo(self):
        """Get the repository if it exists, otherwise raise a custom Exception
        """
        try:
            repo = git.Repo(self.repo_path)
        except Exception:
            raise Exception(f"Configuration repository not found at [{self.repo_path}]")

        return repo


class ConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.configuration_dir)


class GeneratedConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.get_generated_configuration_dir())

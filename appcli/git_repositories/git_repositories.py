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

BRANCH_NAME_FORMAT: str = "deployment/{version}"

# ------------------------------------------------------------------------------
# PUBLIC CLASSES
# ------------------------------------------------------------------------------


class GitRepository:
    """Class which encapsulates different git repo actions for configuration repositories"""

    def __init__(self, repo_path: Path, ignores: Iterable[str] = []):
        self.actor: git.Actor = git.Actor("appcli", "root@localhost")
        self.repo_path = repo_path
        self.ignores = ignores

    def initialise_git_repo(self):
        # Initialise the git repository, create .gitignore if required, and commit the initial files
        logger.debug("Initialising repository at [%s] ...", self.repo_path)

        if self.repo_exists():
            raise Exception(
                f"Cannot 'git init'. Git repo already exists at [{self.repo_path}]."
            )

        # git init, and write to the .gitignore file
        repo = git.Repo.init(self.repo_path)
        logger.debug("Initialised repository at [%s]", repo.working_dir)

        gitignore_path = self.repo_path.joinpath(".gitignore")
        with open(gitignore_path, "w") as ignore_file:
            for ignore in self.ignores:
                ignore_file.write(f"{ignore}\n")
        logger.debug(
            f"Created .gitignore at [{gitignore_path}] with ignores: [%s]", self.ignores
        )

        repo.git.add(".gitignore")
        repo.git.add("*")
        repo.index.commit("[autocommit] Initialised repository", author=self.actor)

    def repo_exists(self) -> bool:
        try:
            git.Repo(self.repo_path)
            return True
        except git.InvalidGitRepositoryError:
            return False

    def commit_changes(self, message: str) -> bool:
        """Commit the existing changes to the git repository

        Args:
            message (str): The commit message to use

        Returns:
            bool: True if a commit was made, otherwise False.

        """
        repo = self.__get_repo()

        # If the repo isn't dirty, don't commit
        if not repo.is_dirty(untracked_files=True):
            logger.debug(
                "No changes found in repository [%s], no commit was made.",
                repo.working_dir,
            )
            return False

        logger.debug(
            "Changes found in repository [%s], making new commit.",
            repo.working_dir,
        )

        repo.git.add(".gitignore")
        repo.git.add("*")
        repo.index.commit(message, author=self.actor)
        return True

    def checkout_new_branch_from_master(self, branch_name: str):
        """Checkout a new branch from the HEAD of master

        Args:
            branch_name (str): name of the new branch
        """
        repo = self.__get_repo()
        self.checkout_existing_branch("master")
        repo.git.checkout("HEAD", b=branch_name)

    def checkout_existing_branch(self, branch_name: str):
        """Checkout an existing branch

        Args:
            branch_name (str): name of the branch to checkout to
        """
        repo = self.__get_repo()
        repo.git.checkout(branch_name)

    def get_repository_version(self) -> str:
        """Get the nominal 'version' associated with this git repository. This is not a 'git'
        concept, but rather an 'appcli' concept for what 'version' the repository is using.

        Returns:
            str: the 'appcli-specific' version of this particular git repository, which aligns
                with the version of the application.
        """
        # Version is stored as part of the branch name, strip it by generating a blank
        # branch name and trimming that from the start of the current branch name
        branch_name: str = self.__get_current_branch_name()
        branch_leading_characters = self.generate_branch_name("")
        return branch_name.split(branch_leading_characters)[-1]

    def does_branch_exist(self, branch_name: str) -> bool:
        """Checks if a branch with a particular name exists

        Args:
            branch_name (str): the name of the branch to check

        Returns:
            bool: True if the branch exists, otherwise false
        """
        repo = self.__get_repo()
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
        repo = self.__get_repo()
        repo.git.tag(tag_name)

    def is_dirty(self, untracked_files: bool = False):
        """Tests if the repository is dirty or not. True if dirty, False if not.

        Args:
            untracked_files (bool, optional): Whether the check includes untracked files. Defaults to False.

        Returns:
            [bool]: True if repository is considered dirty, False otherwise.
        """
        repo = self.__get_repo()
        return repo.is_dirty(untracked_files=untracked_files)

    def get_current_commit_hash(self):
        """Get the commit hash of the current commit"""
        repo = self.__get_repo()
        return repo.git.rev_parse("HEAD")

    def get_diff_to_tag(self, tag: str, diff_dir: str = ""):
        repo = self.__get_repo()
        return repo.git.diff(f"tags/{tag}", f"{diff_dir}")

    def rename_current_branch(self, branch_name: str):
        """Renames the current branch

        Args:
            branch_name (str): the new branch name
        """
        repo = self.__get_repo()
        repo.git.branch(m=branch_name)
        logger.debug(f"Renamed branch to [{branch_name}]")

    def generate_branch_name(self, version="latest") -> str:
        """Generate the name of the branch based on the 'appcli' naming convention and version number

        Args:
            version (str): The version number to use in the branch.
        Returns:
            str: name of the branch

        """
        return BRANCH_NAME_FORMAT.format(version=version)

    def get_repo_path(self):
        return self.repo_path

    def __get_repo(self) -> git.Repo:
        return git.Repo(self.repo_path)

    def __get_current_branch_name(self) -> str:
        """Get the name of the current branch

        Returns:
            str: name of the current branch
        """
        repo = self.__get_repo()
        return repo.git.symbolic_ref("HEAD", short=True).replace("heads/", "")


class ConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(
            cli_context.configuration_dir,
            [".generated*", ".metadata*"],
        )


class GeneratedConfigurationGitRepository(GitRepository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.get_generated_configuration_dir())

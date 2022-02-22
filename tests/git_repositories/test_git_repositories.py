#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for git_repositories.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# local libraries
from appcli.git_repositories.git_repositories import GitRepository

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

BRANCH_NAME_PREFIX = "deployment/"

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_can_get_version_from_branch_default(monkeypatch, tmpdir):
    git_repo = get_uninitialised_git_repository(monkeypatch, tmpdir)
    branch_name = git_repo.generate_branch_name
    monkeypatch.setattr(
        "appcli.git_repositories.git_repositories.GitRepository._GitRepository__get_current_branch_name",
        branch_name,
    )

    version = git_repo.get_repository_version()

    assert "latest" == version


def test_can_get_version_from_branch_with_version(monkeypatch, tmpdir):
    git_repo = get_uninitialised_git_repository(monkeypatch, tmpdir)
    branch_name = git_repo.generate_branch_name("1.0")
    monkeypatch.setattr(
        "appcli.git_repositories.git_repositories.GitRepository._GitRepository__get_current_branch_name",
        lambda x: branch_name,
    )

    version = git_repo.get_repository_version()

    assert "1.0" == version


def test_can_not_fail_getting_version_from_branch_unexpected_start(monkeypatch, tmpdir):
    """In cases where we are unable to strip the expected start from the branch name use the entire branch name as the version."""
    git_repo = get_uninitialised_git_repository(monkeypatch, tmpdir)
    branch_name = git_repo.generate_branch_name("1.0")
    monkeypatch.setattr(
        "appcli.git_repositories.git_repositories.GitRepository._GitRepository__get_current_branch_name",
        lambda x: branch_name,
    )
    monkeypatch.setattr(
        "appcli.git_repositories.git_repositories.GitRepository.generate_branch_name",
        lambda x, y: "feature/",
    )

    version = git_repo.get_repository_version()

    assert f"{BRANCH_NAME_PREFIX}1.0" == version


def test_branch_name_as_expected_with_version(monkeypatch, tmpdir):
    git_repo = get_uninitialised_git_repository(monkeypatch, tmpdir)

    branch_name = git_repo.generate_branch_name("1.0")

    assert f"{BRANCH_NAME_PREFIX}1.0" == branch_name


def test_branch_name_as_expected_no_version(monkeypatch, tmpdir):
    git_repo = get_uninitialised_git_repository(monkeypatch, tmpdir)

    branch_name = git_repo.generate_branch_name()

    assert f"{BRANCH_NAME_PREFIX}latest" == branch_name


def test_branch_name_as_expected_empty_version(monkeypatch, tmpdir):
    git_repo = get_uninitialised_git_repository(monkeypatch, tmpdir)

    branch_name = git_repo.generate_branch_name("")

    assert f"{BRANCH_NAME_PREFIX}" == branch_name


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def get_uninitialised_git_repository(monkeypatch, tmpdir):
    monkeypatch.setattr(
        "appcli.git_repositories.git_repositories.GitRepository.__init__",
        lambda x, y: None,
    )
    return GitRepository(tmpdir)

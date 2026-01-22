#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for the archive manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

# Standard libraries.
from pathlib import Path
import datetime
import tarfile
import os

# Vendor libraries.
import pytest

# Local libraries.
from appcli.stack_manager.archive_manager import ArchiveManager, CompressRule
from appcli.models.cli_context import CliContext


# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME_ENV_VAR = "APP_NAME"
APP_NAME_ENV_VALUE = "myapp"

# DATA

DATA_DIR = {
    "app": {
        "a.txt": None,
        "b.yml": None,
    },
    "app.txt": None,
    ".hidden": {
        ".hidden.txt": None,
    },
}
"""Data directory structure for testing."""


# RULES

EMPTY_CONFIG = []
"""No archiving configuration."""

EMPTY_RULESET = {
    "name": "empty",
    "rules": [],
}
"""Ruleset with no actual rules."""

PURGE_RULE = {
    "name": "purge_txt",
    "type": "purge",
    "include_list": ["**/*.txt"],
}
"""Purge rule."""

COMPRESS_RULE = {
    "name": "compress_txt",
    "type": "compress",
    "include_list": ["**/*.txt"],
    "archive_file": "archive/file-%Y%m-${APP_NAME}.tgz",
}
"""Compress rule."""

COMPRESS_DEFAULT = {
    "name": "compress_default",
    "type": "compress",
}
"""A compress rule with only required values set."""

SINGLE_RULESET = [
    {"name": "all", "rules": [PURGE_RULE, COMPRESS_RULE]},
]
"""One monolith ruleset consisting of all the rules."""

MULTIPLE_RULESET = [
    {
        "name": "compress_rule",
        "rules": [COMPRESS_RULE],
    },
    {
        "name": "purge_rule",
        "rules": [PURGE_RULE],
    },
]
"""Multiple rulesets each containing a single rule."""


# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


def dict_to_tmpdir(tmp_path, directory_dict):
    """Instantiate a tmpdir based off a nested python dict."""

    def create_items(base, items):
        for name, value in items.items():
            path = base / name
            if isinstance(value, dict):
                path.mkdir()
                create_items(path, value)
            else:
                path.touch()

    create_items(tmp_path, directory_dict)
    return tmp_path


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


@pytest.fixture(scope="function")
def create_data_dir(tmp_path):
    return dict_to_tmpdir(tmp_path, DATA_DIR)


@pytest.fixture()
def create_cli_context(create_data_dir):
    return CliContext(
        configuration_dir=None,
        application_context_files_dir=None,
        data_dir=create_data_dir,
        backup_dir=None,
        app_name_slug="test_app",
        additional_data_dirs=None,
        additional_env_variables=None,
        environment="test",
        docker_credentials_file=None,
        subcommand_args=None,
        debug=True,
        is_dev_mode=False,
        app_version="1.0",
        commands=None,
    )


@pytest.fixture(scope="function")
def set_app_name():
    """Set and unset the APP_NAME environment variable."""
    os.environ[APP_NAME_ENV_VAR] = APP_NAME_ENV_VALUE
    try:
        yield
    finally:
        del os.environ[APP_NAME_ENV_VAR]


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_no_rulesets(create_cli_context, capsys):
    """Test running all rulesets when none are defined."""
    archive_manager = ArchiveManager(create_cli_context, EMPTY_CONFIG)

    archive_manager.run_all_archive_rulesets()
    captured = capsys.readouterr()
    assert "No rules defined in the stack settings." in captured.err


def test_non_existant_ruleset(create_cli_context):
    """Test running a ruleset that does not exist."""
    archive_manager = ArchiveManager(create_cli_context, EMPTY_CONFIG)

    error_msg = "The archive rule `norule` was not found in the `stack-settings` file."
    with pytest.raises(KeyError, match=error_msg):
        archive_manager.run_archive_ruleset("norule")


def test_duplicate_ruleset(create_cli_context):
    """Test when the same ruleset is defined multiple times."""
    archive_manager = ArchiveManager(create_cli_context, [EMPTY_RULESET, EMPTY_RULESET])

    error_msg = (
        "Multiple rules matching `empty` were found in the `stack-settings` file."
    )
    with pytest.raises(KeyError, match=error_msg):
        archive_manager.run_archive_ruleset("empty")


def test_runtime_order(create_cli_context, set_app_name):
    """Test that the rules are run in the order they are defined."""
    archive_manager = ArchiveManager(create_cli_context, SINGLE_RULESET)
    archive_manager.run_archive_ruleset("all")
    # NOTE: We need the current datetime to calculate the generated archive filename.
    # It wont be exactly the same, but the filename uses the `year/month` so only those need to be correct.
    runtime = datetime.datetime.now()

    data_dir = create_cli_context.data_dir
    archive_file = Path(
        data_dir / f"archive/file-{runtime.strftime('%Y%m')}-{APP_NAME_ENV_VALUE}.tgz"
    )

    # Get a list of all the archived files.
    files = []
    with tarfile.open(archive_file, "r:gz") as tar:
        files = tar.getnames()

    # All `.txt` files should have been purged BEFORE they could be archived.
    assert not Path(data_dir / "app/a.txt").exists()
    assert "app/a.txt" not in files


def test_only_run_specific_ruleset(create_cli_context, capsys, set_app_name):
    """Test that only the specified ruleset is called."""
    archive_manager = ArchiveManager(create_cli_context, MULTIPLE_RULESET)
    archive_manager.run_archive_ruleset("purge_rule")
    captured = capsys.readouterr()
    # NOTE: We need the current datetime to calculate the generated archive filename.
    # It wont be exactly the same, but the filename uses the `year/month` so only those need to be correct.
    runtime = datetime.datetime.now()

    data_dir = create_cli_context.data_dir
    archive_file = Path(
        data_dir / f"archive/file-{runtime.strftime('%Y%m')}-{APP_NAME_ENV_VALUE}.tgz"
    )
    # Check purge rule was run.
    assert "Executing the `purge_rule.purge_txt` archiving rule." in captured.err
    assert not Path(data_dir / "app/a.txt").exists()

    # Check compress rule was not run.
    assert (
        "Executing the `compress_rule.compress_txt` archiving rule." not in captured.err
    )
    assert not archive_file.exists()


def test_purge(create_cli_context, capsys):
    """Test the purge rule."""
    archive_manager = ArchiveManager(create_cli_context, MULTIPLE_RULESET)
    archive_manager.run_archive_ruleset("purge_rule")
    captured = capsys.readouterr()

    data_dir = create_cli_context.data_dir
    assert "Executing the `purge_rule.purge_txt` archiving rule." in captured.err
    assert "Removing the following files:" in captured.err
    # Check that we are only getting `.txt` files.
    assert not Path(data_dir / "app/a.txt").exists()
    assert Path(data_dir / "app/b.yml").exists()
    # The pattern requires recursion, so ignore root level matches.
    assert Path(data_dir / "app.txt").exists()
    # Hidden files should be ignored.
    assert Path(data_dir / ".hidden/.hidden.txt").exists()


def test_compress(create_cli_context, capsys, set_app_name):
    """Test the compress rule."""
    archive_manager = ArchiveManager(create_cli_context, MULTIPLE_RULESET)
    archive_manager.run_archive_ruleset("compress_rule")
    captured = capsys.readouterr()
    # NOTE: We need the current datetime to calculate the generated archive filename.
    # It wont be exactly the same, but the filename uses the `year/month` so only those need to be correct.
    runtime = datetime.datetime.now()

    data_dir = create_cli_context.data_dir
    archive_file = Path(
        data_dir / f"archive/file-{runtime.strftime('%Y%m')}-{APP_NAME_ENV_VALUE}.tgz"
    )
    assert "Executing the `compress_rule.compress_txt` archiving rule." in captured.err
    assert "Archive created at" in captured.err
    assert archive_file.exists()

    # Get a list of all the archived files.
    files = []
    with tarfile.open(archive_file, "r:gz") as tar:
        files = tar.getnames()

    # Check that we are only getting `.txt` files.
    assert "app/a.txt" in files
    assert "app/b.yml" not in files
    # The pattern requires recursion, so ignore root level matches.
    assert "app.txt" not in files
    # Hidden files should be ignored.
    assert ".hidden/.hidden.txt" not in files


def test_default_compress(set_app_name):
    """Test a default compress rule to make sure the naming is correct."""
    rule_config: CompressRule = CompressRule.model_validate(COMPRESS_DEFAULT)
    # NOTE: We need the current datetime to calculate the generated archive filename.
    # It wont be exactly the same, but the filename uses the `year/month` so only those need to be correct.
    runtime = datetime.datetime.now()

    assert (
        rule_config.archive_file
        == f"{runtime.strftime('%Y-%m%d')}_{APP_NAME_ENV_VALUE}.tgz"
    )

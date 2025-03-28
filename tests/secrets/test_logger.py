#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests printing secrets through the logger.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

# Vendor imports.
import pytest
import tempfile
import os
import logging

# Local imports.
from appcli.logger import logger


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


@pytest.fixture
def log_file_setup():
    # Use a temp file for the log
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test.log")

        # Create a file handler
        file_handler = logging.FileHandler(log_path)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        yield log_path  # Provide the path to the test

        # Teardown: remove handler
        logger.removeHandler(file_handler)


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_base64_encoded(capsys):
    """Make sure the secret value is Base64 encoded."""
    logger.sensitive("key", "value")
    output = capsys.readouterr()

    assert "[SENSITIVE]" in output.err
    assert "dmFsdWU=" in output.err  # "value" encoded as Base64
    assert "value" not in output.err


def test_log_to_file(log_file_setup):
    """Ensure secrets are not being written to file,
    even when a filehandler is explicitly attached.
    """
    logger.info("Username: Admin")
    logger.sensitive("Password", "p@ssword123")
    logger.info("Host: machine.local")
    with open(log_file_setup, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Admin" in content
    assert "p@ssword123" not in content
    assert "cEBzc3dvcmQxMjM=" not in content  # "p@ssword123" encoded as Base64
    assert "machine.local" in content  # Check logger settings correctly reverted.

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Common functions.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import click
import re
import sys
from typing import Iterable, Any

# local libraries
from appcli.logger import logger
from appcli.models.cli_context import CliContext


# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

METADATA_FILE_NAME = "metadata-configure.json"
""" Name of the file holding metadata from running a configure (relative to the generated configuration directory) """

# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------


def error_and_exit(message: str):
    """Exit with an error message

    Args:
        message (str): [description]
    """
    logger.error(message)
    sys.exit(1)


def get_metadata_file_directory(cli_context: CliContext):
    generated_configuration_dir = cli_context.generated_configuration_dir
    return generated_configuration_dir.joinpath(METADATA_FILE_NAME)


def check_valid_environment_variable_names(
    ctx: click.Context, param: click.Option, value: click.Tuple
):
    """Callback for Click Options to check environment variables are named appropriately for bash

    Args:
        ctx (click.Context): current cli context
        param (click.Option): the option parameter to validate
        value (click.Tuple): the values passed to the option
    """
    variable_names: Iterable[str] = [x[0] for x in value]
    errors = []
    for name in variable_names:
        if not re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name):
            errors.append(name)

    if errors:
        error_and_exit(
            f"Invalid environment variable name(s) supplied '{errors}'. Names may only contain alphanumeric characters and underscores."
        )

    # Return the validated values
    return value

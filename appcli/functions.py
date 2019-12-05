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

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
# VARIABLES
# ------------------------------------------------------------------------------

# Regex will match a valid environment variable name (in bash), followed by '='
# and any value
ENV_VAR_REGEX = re.compile("^([a-zA-Z][a-zA-Z0-9_]*?)=(.*)$")

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


def extract_valid_environment_variable_names(
    ctx: click.Context, param: click.Option, values: click.Tuple
):
    """Callback for Click Options to extract environment variable names and values,
    and to check that the names are appropriate for bash

    Args:
        ctx (click.Context): current cli context
        param (click.Option): the option parameter to validate
        values (click.Tuple): the values passed to the option, could be multiple
    """
    
    errors = []
    output = ()
    for keyvalue in values:
        match = ENV_VAR_REGEX.search(keyvalue)
        if not match:
            errors.append(keyvalue)
        else:
            output += (match.groups(),)

    if errors:
        error_and_exit(
            f"Invalid environment variable name(s) supplied '{errors}'. Names may only contain alphanumeric characters and underscores."
        )

    # Return the extracted values
    return output

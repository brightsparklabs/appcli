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
from pathlib import Path
import re
import sys
from typing import Callable, Iterable

# local libraries
from appcli.logger import logger
from appcli.models.cli_context import CliContext

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

METADATA_FILE_NAME = "metadata-configure-apply.json"
""" Name of the file holding metadata from running a configure (relative to the generated configuration directory) """

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


def get_generated_configuration_metadata_file(cli_context: CliContext) -> Path:
    generated_configuration_dir = cli_context.get_generated_configuration_dir()
    return generated_configuration_dir.joinpath(METADATA_FILE_NAME)


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

    # Remove duplicates (last one takes precedence) and return
    deduplicated = {k: v for k, v in output}
    return tuple((k, deduplicated[k]) for k in sorted(deduplicated.keys()))


def validate(
    cli_context: CliContext,
    blocking_checks: Iterable[Callable[[click.Context], None]] = [],
    forceable_checks: Iterable[Callable[[click.Context], None]] = [],
    force: bool = False,
):
    """Perform validation checks, and exit if failed (and not overridden)
    
    Args:
        cli_context (CliContext): the current cli context
        blocking_checks (Iterable[Callable[[click.Context], None]], optional): The check functions to run that are not '--force'able. Defaults to [].
        forceable_checks (Iterable[Callable[[click.Context], None]], optional): The check functions to run that are '--force'able. Defaults to [].
        force (bool, optional): Whether to force pass any forceable_checks that fail. Defaults to False.
    """
    logger.info("Performing validation ...")

    blocking_errors = _run_checks(cli_context, blocking_checks)
    blocking_error_messages = "\n- ".join(blocking_errors)

    forceable_errors = _run_checks(cli_context, forceable_checks)
    forceable_error_messages = "\n- ".join(forceable_errors)

    all_errors = blocking_errors + forceable_errors

    if not all_errors:
        logger.debug("No errors found in validation.")
        return

    if not blocking_errors and forceable_errors and force:
        logger.warn(
            "Force flag `--force` applied. Ignoring the following issues:\n- %s",
            forceable_error_messages,
        )
        return

    output_error_message = "Errors found during validation.\n\n"
    if forceable_errors:
        output_error_message += f"Force-able issues:\n- {forceable_error_messages}\nUse the `--force` flag to ignore these issues.\n\n"
    if blocking_errors:
        output_error_message += f"Blocking issues (these cannot be bypassed and must be fixed):\n- {blocking_error_messages}\n\n"
    output_error_message += "Validation failed. See error messages above."
    error_and_exit(output_error_message)


def _run_checks(
    cli_context: CliContext, checks: Iterable[Callable[[click.Context], None]]
):
    errors = []
    for check in checks:
        check_name = check.__name__
        try:
            logger.debug(f"Running check: [{check_name}]")
            check(cli_context)
            logger.debug(f"PASSED [{check_name}]")
        except Exception as e:
            errors.append(str(e))
            logger.debug(f"FAILED [{check_name}]")
    return errors

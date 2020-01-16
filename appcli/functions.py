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
from typing import Callable, Iterable, List

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


def print_header(title):
    logger.info(
        """============================================================
                        %s
                        ============================================================""",
        title.upper(),
    )


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
    must_have_checks: Iterable[Callable[[click.Context], None]] = [],
    should_have_checks: Iterable[Callable[[click.Context], None]] = [],
    force: bool = False,
):
    """Perform validation checks, and exit if failed (and not overridden)

    Args:
        cli_context (CliContext): the current cli context
        must_have_checks (Iterable[Callable[[click.Context], None]], optional): The check functions to run that are not '--force'able. Defaults to [].
        should_have_checks (Iterable[Callable[[click.Context], None]], optional): The check functions to run that are '--force'able. Defaults to [].
        force (bool, optional): Whether to force pass any should_have_checks that fail. Defaults to False.
    """
    logger.info("Performing validation ...")

    # Get the blocking errors
    blocking_errors = _run_checks(cli_context, must_have_checks)
    blocking_error_messages = "\n- ".join(blocking_errors)

    # Get the non-blocking errors - 'warnings'
    forceable_errors = _run_checks(cli_context, should_have_checks)
    forceable_error_messages = "\n- ".join(forceable_errors)

    all_errors = blocking_errors + forceable_errors

    # If there's no errors, validation ends here and is successful
    if not all_errors:
        logger.debug("No errors found in validation.")
        return

    # If there's no blocking errors, and there's forceable errors and the force flag is provided, warn the user
    # but succeed in validation.
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
) -> List[str]:
    """Runs a set of functions which either return None or throws an error. Returns all the error messages.

    Args:
        cli_context (CliContext): the current context of the cli
        checks (Iterable[Callable[[click.Context], None]]): a set of functions to try running

    Returns:
        List[str]: List of error messages. Could be an empty list.
    """
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

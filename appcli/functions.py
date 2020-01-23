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
from typing import Callable, Iterable, List

# local libraries
from appcli.logger import logger
from appcli.models.cli_context import CliContext

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


def execute_validation_functions(
    cli_context: CliContext,
    must_succeed_checks: Iterable[Callable[[click.Context], None]] = [],
    should_succeed_checks: Iterable[Callable[[click.Context], None]] = [],
    force: bool = False,
):
    """Run validation check functions. There are two types of checks: 'must' checks and 'should' checks.

    'Must' check functions must complete and exit without raising Exceptions, or else the whole validation check will fail.

    'Should' check functions should completed and exit without raising Exceptions. If any Exceptions are raised, and 'force' is False,
    then this validation check will fail. If Exceptions are raised and 'force' is True, then these are raised as warning to the user
    but the validation is successful.

    All the 'Must' and 'Should' checks (taking into account 'force') need to succeed in order for this validation to be successful.

    Args:
        cli_context (CliContext): the current cli context
        must_succeed_checks (Iterable[Callable[[click.Context], None]], optional): The check functions to run which must not raise any exceptions
            in order for the validation to succeed.
        should_succeed_checks (Iterable[Callable[[click.Context], None]], optional): The check functions to run, which may raise exceptions. If
            'force' is True, any Exceptions are displayed as 'warnings' and won't fail the validation check. If 'force' is False, any Exceptions
            will failed the validation.
        force (bool, optional): Whether to ignore any should_succeed_checks which fail. Defaults to False.
    """
    logger.info("Performing validation ...")

    # Get the blocking errors
    must_succeed_errors = _run_checks(cli_context, must_succeed_checks)
    must_succeed_error_messages = "\n- ".join(must_succeed_errors)

    # Get the non-blocking errors - 'warnings'
    should_succeed_errors = _run_checks(cli_context, should_succeed_checks)
    should_succeed_error_messages = "\n- ".join(should_succeed_errors)

    all_errors = must_succeed_errors + should_succeed_errors

    # If there's no errors, validation ends here and is successful
    if not all_errors:
        logger.debug("No errors found in validation.")
        return

    # If there's errors in the 'should' checks and force is True, then only warn for those errors
    if should_succeed_errors and force:
        logger.warn(
            "Force flag `--force` applied. Ignoring the following issues:\n- %s",
            should_succeed_error_messages,
        )
        # If there's no 'must' errors now, validation is successful
        if not must_succeed_errors:
            return

    output_error_message = "Errors found during validation.\n\n"

    # If there's forced 'should' errors, then we've already warned, and don't need to include this in the error message
    if should_succeed_errors and not force:
        output_error_message += f"Force-able issues:\n- {should_succeed_error_messages}\nUse the `--force` flag to ignore these issues.\n\n"
    if must_succeed_errors:
        output_error_message += f"Blocking issues (these cannot be bypassed and must be fixed):\n- {must_succeed_error_messages}\n\n"
    output_error_message += "Validation failed. See error messages above."
    error_and_exit(output_error_message)


def _run_checks(
    cli_context: CliContext, checks: Iterable[Callable[[click.Context], None]]
) -> List[str]:
    """Runs a set of functions which either return None or raises an Exception. Returns all Exception error messages.

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

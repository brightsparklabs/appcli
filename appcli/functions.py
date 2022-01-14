#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Common functions.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import re
from pathlib import Path

# vendor libraries
import click

# local libraries
from appcli.crypto import crypto
from appcli.crypto.cipher import Cipher
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
    # Raise a SystemExit exception with another exception with the error message
    # as the code so we can capture it externally.
    raise SystemExit(1) from SystemExit(message)


def print_header(title):
    logger.info(
        """
============================================================
%s
============================================================""",
        title.upper(),
    )


def encrypt_text(cli_context, text: str):
    """Encrypts text using application key file.

    Args:
        cli_context (CliContext): the cli context
        text (str): the string to encrypt
    """
    if text is None:
        raise ValueError("Text to encrypt cannot be 'None'")

    key_file: Path = cli_context.get_key_file()
    if not key_file.is_file():
        logger.debug("Creating encryption key at [%s]", key_file)
        crypto.create_and_save_key(key_file)

    cipher = Cipher(key_file)
    return cipher.encrypt(text)


def extract_valid_environment_variable_names(
    ctx: click.Context, param: click.Option, values: click.Tuple
):
    """Callback for Click Options to extract environment variable names and values,
    and to check that the names are appropriate for bash

    Args:
        ctx (click.Context): current CLI context
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

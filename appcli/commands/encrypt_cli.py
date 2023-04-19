#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The encrypt command available when running the CLI.

Responsible for encrypting strings.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import click
from click.core import Context

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.functions import encrypt_text
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class EncryptCli:
    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.configuration: Configuration = configuration

        @click.command(help="Encrypts the specified string.")
        @click.argument("text", required=False)
        @click.pass_context
        def encrypt(ctx: Context, text: str = None):
            """Encrypt a string using the application keyfile.

            Args:
                ctx (Context): Click Context for current CLI.
                text (str): The text to encrypt
            """
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.ENCRYPT
            )
            # Check if value was not provided
            if text is None:
                text = click.prompt("Please enter a value to encrypt", type=str)
            print(encrypt_text(cli_context, text))

        # expose the CLI command
        self.commands = {"encrypt": encrypt}

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The encrypt command available when running the CLI.

Responsible for encrypting strings.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
from pathlib import Path

# vendor libraries
import click

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.crypto import crypto
from appcli.crypto.cipher import Cipher
from appcli.logger import logger
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
        @click.argument("text")
        @click.pass_context
        def encrypt(ctx, text: str):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.ENCRYPT
            )
            key_file: Path = cli_context.get_key_file()
            if not key_file.is_file():
                logger.info("Creating encryption key at [%s]", key_file)
                crypto.create_and_save_key(key_file)

            cipher = Cipher(key_file)
            result = cipher.encrypt(text)
            print(result)

        # expose the CLI command
        self.commands = {"encrypt": encrypt}

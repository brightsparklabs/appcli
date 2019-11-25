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
import os
from pathlib import Path

# vendor libraries
import click

# local libraries
import appcli.crypter as crypter
from appcli.logger import logger
from appcli.models import CliContext, Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class EncryptCli:

    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):

        self.configuration: Configuration = configuration

        @click.command(help="Encrypts the specified string")
        @click.argument("text")
        @click.pass_context
        def encrypt(ctx, text: str):

            cli_context: CliContext = ctx.obj
            key_file: Path = Path(cli_context.configuration_dir, "key")
            if not key_file.is_file():
                logger.info("Creating encryption key at [%s]", key_file)
                crypter.create_and_save_key(key_file)

            cipher = crypter.Cipher(key_file)
            result = cipher.encrypt(text)
            print(result)

        # expose the cli command
        self.commands = {"encrypt": encrypt}

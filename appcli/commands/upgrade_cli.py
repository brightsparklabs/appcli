#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The Upgrade command available when running the CLI.

Responsible for upgrading the application to a newer version.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library

# vendor libraries
import click

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class UpgradeCli:

    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        @click.command(
            help="Upgrades the application configuration to work with the current application version (deprecated - use upgrage).", hidden=True
        )
        @click.pass_context
        def migrate(ctx):
            self.__upgrade(ctx)

        @click.command(
            help="Upgrades the application configuration to work with the current application version.",
        )
        @click.pass_context
        def upgrade(ctx):
            self.__upgrade(ctx)

        # expose the cli command
        self.commands = {
            "migrate": migrate,
            "upgrade": upgrade
        }

    def __upgrade(self, ctx):
        cli_context: CliContext = ctx.obj

        # Perform upgrade
        ConfigurationManager(
            cli_context, self.cli_configuration
        ).upgrade_configuration()

        logger.info("Upgrade complete.")

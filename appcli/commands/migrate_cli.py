#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The migrate command available when running the CLI.

Responsible for migrating the application to a newer version.
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


class MigrateCli:

    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        @click.command(
            help="Migrates the application configuration to work with the current application version. Alias of 'upgrade'.",
        )
        @click.pass_context
        def migrate(ctx):
            self.__migrate(ctx)

        @click.command(
            help="Upgrades the application configuration to work with the current application version. Alias of 'migrate'.",
        )
        @click.pass_context
        def upgrade(ctx):
            self.__migrate(ctx)

        # expose the cli command
        self.commands = {"migrate": migrate, "upgrade": upgrade}

    def __migrate(self, ctx):
        cli_context: CliContext = ctx.obj

        # Perform migration
        ConfigurationManager(
            cli_context, self.cli_configuration
        ).migrate_configuration()

        logger.info("Migration complete.")

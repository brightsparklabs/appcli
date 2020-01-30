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
from appcli.models.configuration import Configuration
from appcli.models.cli_context import CliContext

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
            help="Migrates the application configuration to work with the current application version."
        )
        @click.pass_context
        def migrate(ctx):

            cli_context: CliContext = ctx.obj

            # Perform migration
            ConfigurationManager(
                cli_context, self.cli_configuration
            ).migrate_configuration()

            logger.info(f"Migration complete.")

        # expose the cli command
        self.commands = {"migrate": migrate}

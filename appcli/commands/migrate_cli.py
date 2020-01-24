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
from appcli.configuration_manager import (
    ConfigurationManager,
    confirm_config_dir_is_not_dirty,
    confirm_generated_config_dir_is_not_dirty,
    confirm_generated_configuration_is_using_current_configuration,
    confirm_generated_config_dir_exists,
)
from appcli.functions import execute_validation_functions
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

            # Validate environment
            self.__pre_migrate_validation(cli_context)

            # Perform migration
            ConfigurationManager(cli_context, self.cli_configuration).migrate()

            logger.info(f"Migration successfully completed.")

        # expose the cli command
        self.commands = {"migrate": migrate}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __pre_migrate_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for migration.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.info("Checking system configuration is valid before migration ...")

        should_succeed_checks = []

        # If the generated configuration directory exists, test it for 'dirtiness'.
        # Otherwise the generated config doesn't exist, so the directories are 'clean'.
        try:
            confirm_generated_config_dir_exists(cli_context)
            # If the generated config is dirty, or not running against current config, warn before overwriting
            should_succeed_checks = [
                confirm_generated_config_dir_is_not_dirty,
                confirm_generated_configuration_is_using_current_configuration,
            ]
        except Exception:
            # If the confirm fails, then we just pass as this is an expected error
            pass

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=[confirm_config_dir_is_not_dirty],
            should_succeed_checks=should_succeed_checks,
        )

        logger.info("System configuration is valid for migration.")

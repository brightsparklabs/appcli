#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configures the system.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import os
from typing import Iterable

# vendor libraries
import click

# local libraries
from appcli.configuration_manager import (
    ConfigurationManager,
    confirm_config_dir_exists,
)
from appcli.functions import (
    error_and_exit,
    execute_validation_functions,
    print_header,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigureCli:
    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        self.app_name = self.cli_configuration.app_name

        env_config_dir = f"{self.app_name}_CONFIG_DIR".upper()
        env_data_dir = f"{self.app_name}_DATA_DIR".upper()
        self.mandatory_env_variables = (env_config_dir, env_data_dir)

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(invoke_without_command=True, help="Configures the application.")
        @click.pass_context
        def configure(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @configure.command(help="Initialises the configuration directory")
        @click.pass_context
        def init(ctx):
            print_header(f"Seeding configuration directory for {self.app_name}")

            cli_context: CliContext = ctx.obj

            # Validate environment
            # TODO: Do we even need this any more? If so, is this the right spot?
            self.__check_env_vars_set(cli_context, self.mandatory_env_variables)

            # Run pre-hooks
            hooks = self.cli_configuration.hooks
            logger.debug("Running pre-configure init hook")
            hooks.pre_configure_init(ctx)

            # Initialise configuration directory
            logger.debug("Initialising configuration directory")
            ConfigurationManager(
                cli_context, self.cli_configuration
            ).initialise_configuration()

            # Run post-hooks
            logger.debug("Running post-configure init hook")
            hooks.post_configure_init(ctx)

            logger.info("Finished initialising configuration")

        @configure.command(help="Applies the settings from the configuration.")
        @click.option(
            "--message",
            "-m",
            help="Message describing the changes being applied.",
            default="[autocommit] due to `configure apply`",
            type=click.STRING,
        )
        @click.option(
            "--force",
            is_flag=True,
            help="Overwrite existing generated configuration, regardless of modified status",
        )
        @click.pass_context
        def apply(ctx, message, force):
            cli_context: CliContext = ctx.obj

            # TODO: run self.cli_configuration.hooks.is_valid_variables() to confirm variables are valid

            # Run pre-hooks
            hooks = self.cli_configuration.hooks
            logger.debug("Running pre-configure apply hook")
            hooks.pre_configure_apply(ctx)

            # Apply changes
            logger.debug("Applying configuration")
            ConfigurationManager(
                cli_context, self.cli_configuration
            ).apply_configuration_changes(message, force=force)

            # Run post-hooks
            logger.debug("Running post-configure apply hook")
            hooks.post_configure_apply(ctx)

            logger.info("Finished applying configuration")

        @configure.command(help="Reads a setting from the configuration.")
        @click.argument("setting")
        @click.pass_context
        def get(ctx, setting):
            cli_context: CliContext = ctx.obj

            # Validate environment
            self.__pre_configure_get_and_set_validation(cli_context)

            # Get settings value and print
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            print(configuration.get_variables_manager().get_variable(setting))

        @configure.command(help="Saves a setting to the configuration.")
        @click.argument("setting")
        @click.argument("value")
        @click.pass_context
        def set(ctx, setting, value):
            cli_context: CliContext = ctx.obj

            # Validate environment
            self.__pre_configure_get_and_set_validation(cli_context)

            # Set settings value
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            configuration.get_variables_manager().set_variable(setting, value)

        # Expose the commands
        self.commands = {"configure": configure}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __check_env_vars_set(
        self, cli_context: CliContext, mandatory_env_variables: Iterable[str]
    ):
        """Check that all mandatory environment variables have been set.

        Args:
            cli_context (CliContext): the current cli context
            mandatory_env_variables (Iterable[str]): the environment variables to check
        """
        logger.info("Checking prerequisites ...")
        has_errors = False

        for env_variable in mandatory_env_variables:
            value = os.environ.get(env_variable)
            if value is None:
                logger.error(
                    "Mandatory environment variable is not defined [%s]", env_variable
                )
                has_errors = True

        if has_errors:
            error_and_exit("Missing mandatory environment variables.")

    def __pre_configure_get_and_set_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for 'configure get'.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.info("Checking system configuration is valid before 'configure get' ...")

        # Block if the config dir doesn't exist as there's nothing to get or set
        must_succeed_checks = [confirm_config_dir_exists]

        execute_validation_functions(
            cli_context=cli_context, must_succeed_checks=must_succeed_checks,
        )

        logger.info("System configuration is valid")

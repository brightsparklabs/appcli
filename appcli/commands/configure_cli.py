#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configures the system.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
from appcli.commands.commands import AppcliCommand
import difflib
import subprocess

# vendor libraries
import click

from appcli.commands.configure_template_cli import ConfigureTemplateCli

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli.functions import print_header
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.string_transformer import StringTransformer

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigureCli:
    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        self.app_name = self.cli_configuration.app_name

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

        @configure.command(help="Initialises the configuration directory.")
        @click.pass_context
        def init(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_INIT
            )

            print_header(f"Seeding configuration directory for {self.app_name}")

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
            help="Overwrite existing generated configuration, regardless of modified status.",
        )
        @click.pass_context
        def apply(ctx, message, force):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_APPLY, force
            )

            # Run pre-hooks
            hooks = self.cli_configuration.hooks
            logger.debug("Running pre-configure apply hook")
            hooks.pre_configure_apply(ctx)

            # Apply changes
            logger.debug("Applying configuration")
            ConfigurationManager(
                cli_context, self.cli_configuration
            ).apply_configuration_changes(message)

            # Run post-hooks
            logger.debug("Running post-configure apply hook")
            hooks.post_configure_apply(ctx)

            logger.info("Finished applying configuration")

        @configure.command(help="Reads a setting from the configuration.")
        @click.argument("setting")
        @click.pass_context
        def get(ctx, setting):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_GET
            )

            # Get settings value and print
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            print(configuration.get_variable(setting))

        @configure.command(help="Saves a setting to the configuration.")
        @click.option(
            "-t",
            "--type",
            type=click.Choice(StringTransformer.get_types()),
            default=StringTransformer.get_string_transformer_type(),
        )
        @click.argument("setting")
        @click.argument("value")
        @click.pass_context
        def set(ctx, type, setting, value):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_SET
            )

            # Transform input value as type
            transformed_value = StringTransformer.transform(value, type)

            # Set settings value
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            configuration.set_variable(setting, transformed_value)
            logger.debug(f"Successfully set variable [{setting}] to [{value}].")

        @configure.command(
            help="Get the differences between current and default configuration settings."
        )
        @click.pass_context
        def diff(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_DIFF
            )

            default_settings_file = self.cli_configuration.seed_app_configuration_file
            current_settings_file = cli_context.get_app_configuration_file()

            default_settings = open(default_settings_file).readlines()
            current_settings = open(current_settings_file).readlines()
            for line in difflib.unified_diff(
                default_settings,
                current_settings,
                fromfile="default",
                tofile="current",
                lineterm="",
            ):
                # remove superfluous \n characters added by unified_diff
                print(line.rstrip())

        @configure.command(help="Open the settings file for editing with vim-tiny.")
        @click.pass_context
        def edit(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_EDIT
            )
            EDITOR = "vim.tiny"

            subprocess.run([EDITOR, cli_context.get_app_configuration_file()])

        # Add the 'template' subcommand
        configure.add_command(ConfigureTemplateCli(self.cli_configuration).command)

        # Expose the commands
        self.commands = {"configure": configure}

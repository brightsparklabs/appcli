#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The main (top-level) commands available when running the CLI.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import sys

# vendor libraries
import click

# local libraries
from appcli.functions import validate
from appcli.git_repositories.git_repositories import (
    confirm_config_dir_is_not_dirty,
    confirm_generated_config_dir_is_not_dirty,
    confirm_generated_config_dir_exists,
    confirm_generated_configuration_is_using_current_configuration,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class MainCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration
        self.orchestrator = configuration.orchestrator

        # ----------------------------------------------------------------------
        # PUBLIC METHODS
        # ----------------------------------------------------------------------

        @click.command(help="Starts the system.")
        @click.option(
            "--force", is_flag=True, help="Force start through validation checks",
        )
        @click.pass_context
        def start(ctx, force):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(ctx)

            cli_context: CliContext = ctx.obj
            self.__pre_start_validation(cli_context, force=force)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.orchestrator.start(ctx.obj)

            logger.debug("Running post-start hook")
            hooks.post_start(ctx, result)

            logger.info("Start command finished with code [%i]", result.returncode)
            sys.exit(result.returncode)

        @click.command(help="Stops the system.")
        @click.option(
            "--force", is_flag=True, help="Force stop through validation checks",
        )
        @click.pass_context
        def stop(ctx, force):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-stop hook")
            hooks.pre_stop(ctx)

            cli_context: CliContext = ctx.obj
            self.__pre_stop_validation(cli_context, force=force)

            logger.info("Stopping %s ...", configuration.app_name)
            result = self.orchestrator.stop(ctx.obj)

            logger.debug("Running post-stop hook")
            hooks.post_stop(ctx, result)

            logger.info("Stop command finished with code [%i]", result.returncode)
            sys.exit(result.returncode)

        # expose the cli commands
        self.commands = {
            "start": start,
            "stop": stop,
            "logs": self.orchestrator.get_logs_command(),
        }

        # create additional group if orchestrator has custom commands
        orchestrator_commands = self.orchestrator.get_additional_commands()
        if len(orchestrator_commands) > 0:

            @click.group(help="Orchestrator specific commands")
            @click.pass_context
            def orchestrator(ctx):
                pass

            for command in orchestrator_commands:
                orchestrator.add_command(command)
            self.commands.update({"orchestrator": orchestrator})

    def __pre_start_validation(self, cli_context: CliContext, force: bool = False):
        """Ensures the system is in a valid state for startup.

        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If True, only warns on validation checks. Defaults to False.
        """
        logger.info("Checking system configuration is valid before starting ...")

        # Only need to block if the generated configuration is not present
        must_have_checks = [confirm_generated_config_dir_exists]

        # If either config dirs are dirty, or generated config doesn't align with
        # current config, then warn before allowing start.
        should_have_checks = [
            confirm_config_dir_is_not_dirty,
            confirm_generated_config_dir_is_not_dirty,
            confirm_generated_configuration_is_using_current_configuration,
        ]

        validate(
            cli_context=cli_context,
            must_have_checks=must_have_checks,
            should_have_checks=should_have_checks,
            force=force,
        )

        logger.info("System configuration is valid")

    def __pre_stop_validation(self, cli_context: CliContext, force: bool = False):
        """Ensures the system is in a valid state for stop.

        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If True, only warns on validation checks. Defaults to False.
        """
        logger.info("Checking system configuration is valid before stopping ...")

        validate(
            cli_context=cli_context,
            must_have_checks=[
                confirm_generated_config_dir_exists
            ],  # Only block stopping the system on the generated config not existing
            force=force,
        )

        logger.info("System configuration is valid")

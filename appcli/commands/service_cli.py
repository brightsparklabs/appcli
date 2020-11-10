#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for lifecycle management of application services.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import sys

# vendor libraries
import click

from appcli.configuration_manager import (
    confirm_generated_config_dir_exists,
    confirm_generated_configuration_is_using_current_configuration,
)

# local libraries
from appcli.functions import execute_validation_functions
from appcli.git_repositories.git_repositories import (
    confirm_config_dir_exists_and_is_not_dirty,
    confirm_config_version_matches_app_version,
    confirm_generated_config_dir_exists_and_is_not_dirty,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ServiceCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration
        self.orchestrator = configuration.orchestrator

        # ----------------------------------------------------------------------
        # PUBLIC METHODS
        # ----------------------------------------------------------------------

        @click.group(
            invoke_without_command=True,
            help="Lifecycle management commands for application services.",
        )
        @click.pass_context
        def service(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @service.command(help="Starts all services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force start even if validation checks fail.",
        )
        @click.pass_context
        def start(ctx, force):
            hooks = self.cli_configuration.hooks

            # TODO: run self.cli_configuration.hooks.is_valid_variables() to confirm variables are valid

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

        @service.command(help="Shuts down all services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force shutdown even if validation checks fail.",
        )
        @click.pass_context
        def shutdown(ctx, force):
            self.__shutdown(ctx, force)

        @service.command(
            help="Stops all services. Alias to 'shutdown' command.", hidden=True
        )
        @click.option("--force", is_flag=True)
        @click.pass_context
        def stop(ctx, force):
            self.__shutdown(ctx, force)

        # Add the 'logs' subcommand
        service.add_command(self.orchestrator.get_logs_command())

        # expose the cli commands
        self.commands = {
            "service": service,
        }

        # create additional group if orchestrator has custom commands
        orchestrator_commands = self.orchestrator.get_additional_commands()
        if len(orchestrator_commands) > 0:

            @click.group(help="Orchestrator specific commands.")
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
            force (bool, optional): If True, only warns on validation failures, rather than exiting
        """
        logger.info("Checking system configuration is valid before starting ...")

        # Only need to block if the generated configuration is not present
        must_succeed_checks = [confirm_generated_config_dir_exists]

        # If either config dirs are dirty, or generated config doesn't align with
        # current config, then warn before allowing start.
        should_succeed_checks = [
            confirm_config_dir_exists_and_is_not_dirty,
            confirm_generated_config_dir_exists_and_is_not_dirty,
            confirm_generated_configuration_is_using_current_configuration,
            confirm_config_version_matches_app_version,
        ]

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=must_succeed_checks,
            should_succeed_checks=should_succeed_checks,
            force=force,
        )

        logger.info("System configuration is valid")

    def __pre_shutdown_validation(self, cli_context: CliContext, force: bool = False):
        """Ensures the system is in a valid state for shutdown.

        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If True, only warns on validation failures, rather than exiting
        """
        logger.info("Checking system configuration is valid before shutting down ...")

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=[
                confirm_generated_config_dir_exists
            ],  # Only block shuting down the system on the generated config not existing
            force=force,
        )

        logger.info("System configuration is valid")

    def __shutdown(self, ctx, force):
        hooks = self.cli_configuration.hooks

        logger.debug("Running pre-shutdown hook")
        hooks.pre_shutdown(ctx)

        cli_context: CliContext = ctx.obj
        self.__pre_shutdown_validation(cli_context, force=force)

        logger.info("Shutting down %s ...", self.cli_configuration.app_name)
        result = self.orchestrator.shutdown(ctx.obj)

        logger.debug("Running post-shutdown hook")
        hooks.post_shutdown(ctx, result)

        logger.info("Shutdown command finished with code [%i]", result.returncode)
        sys.exit(result.returncode)

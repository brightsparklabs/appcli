#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for lifecycle management of application services.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from appcli.commands.commands import AppcliCommand
import sys

# vendor libraries
import click
from click.core import Context

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

        @service.command(help="Starts services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force start even if validation checks fail.",
        )
        @click.argument("service_name", required=False, type=click.STRING)
        @click.pass_context
        def start(ctx, force, service_name):
            cli_context: CliContext = ctx.obj
            cli_context.configuration_state.verify_command_allowed(
                AppcliCommand.SERVICE_START, force
            )

            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(ctx)

            self.__pre_start_validation(cli_context, force=force)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.orchestrator.start(ctx.obj, service_name)

            logger.debug("Running post-start hook")
            hooks.post_start(ctx, result)

            logger.info("Start command finished with code [%i]", result.returncode)
            sys.exit(result.returncode)

        @service.command(help="Shuts down services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force shutdown even if validation checks fail.",
        )
        @click.argument("service_name", required=False, type=click.STRING)
        @click.pass_context
        def shutdown(ctx, force, service_name):
            self.__shutdown(ctx, force, service_name)

        @service.command(help="Stops services.", hidden=True)
        @click.option("--force", is_flag=True)
        @click.argument("service_name", required=False, type=click.STRING)
        @click.pass_context
        def stop(ctx, force, service_name):
            self.__shutdown(ctx, force, service_name)

        # Add the 'logs' subcommand
        service.add_command(self.orchestrator.get_logs_command())

        # expose the CLI commands
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
            cli_context (CliContext): The current CLI context.
            force (bool, optional): If True, only warns on validation failures, rather than exiting.
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
            cli_context (CliContext): The current CLI context.
            force (bool, optional): If True, only warns on validation failures, rather than exiting.
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

    def __shutdown(self, ctx: Context, force: bool = False, service_name: str = None):
        """Shutdown service(s) using the orchestrator.

        Args:
            ctx (Context): Click Context for current CLI.
            force (bool, optional): If True, forcibly shuts down service(s). Defaults to False.
            service_name (str, optional): The name of the service to shutdown. If not provided, will shut down all
                services.
        """
        cli_context: CliContext = ctx.obj
        cli_context.configuration_state.verify_command_allowed(
            AppcliCommand.SERVICE_SHUTDOWN, force
        )

        hooks = self.cli_configuration.hooks

        logger.debug("Running pre-shutdown hook")
        hooks.pre_shutdown(ctx)

        self.__pre_shutdown_validation(cli_context, force=force)

        logger.info("Shutting down %s ...", self.cli_configuration.app_name)
        result = self.orchestrator.shutdown(ctx.obj, service_name)

        logger.debug("Running post-shutdown hook")
        hooks.post_shutdown(ctx, result)

        logger.info("Shutdown command finished with code [%i]", result.returncode)
        sys.exit(result.returncode)

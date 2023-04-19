#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Commands for lifecycle management of application services.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""


# standard libraries
from __future__ import annotations

import enum
import sys

# vendor libraries
import click
from click.core import Context

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ServiceAction(enum.Enum):
    """
    Enum representing avaliable actions to apply to an appcli service or group of services.

    Options:
        START: Start service(s)
        SHUTDOWN: Shutdown service(s)
        STATUS: Get status of service(s)
    """

    START = enum.auto()
    SHUTDOWN = enum.auto()
    STATUS = enum.auto()


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

        @service.command(help="Restarts services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force restart even if validation checks fail.",
        )
        @click.option(
            "--apply",
            is_flag=True,
            help="Do a configure apply after services are stopped",
        )
        @click.argument(
            "service_names",
            required=False,
            type=click.STRING,
            nargs=-1,
            callback=self._validate_service_names,
        )
        @click.pass_context
        def restart(
            ctx: Context, force: bool, apply: bool, service_names: tuple[str, ...]
        ):
            """Restarts service(s)

            Args:
                ctx (Context): Click Context for current CLI.
                force (bool, optional): If True, pass force to all subcommands. Defaults to False.
                apply (bool, optional): If True, configure apply after service(s) are stopped. Defaults to False.
                service_names (tuple[str, ...], optional): The name of the service(s) to restart. If not provided, will restart all
                    services.
            """
            cli_context: CliContext = ctx.obj
            configure_cli = cli_context.commands["configure"]
            # At completion, the invoked commands try to exit the script, so we have to catch
            # the SystemExit exception.
            try:
                ctx.invoke(stop, service_names=service_names)
            except SystemExit:
                pass

            if apply:
                try:
                    ctx.invoke(
                        configure_cli.commands["apply"],
                        message="[autocommit] due to `configure apply` triggered by `service restart --apply`",
                        force=force,
                    )
                except SystemExit:
                    pass

            ctx.invoke(start, force=force, service_names=service_names)

        @service.command(help="Starts services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force start even if validation checks fail.",
        )
        @click.argument(
            "service_names",
            required=False,
            type=click.STRING,
            nargs=-1,
            callback=self._validate_service_names,
        )
        @click.pass_context
        def start(ctx: Context, force: bool, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_START, force
            )
            self._action_orchestrator(ctx, ServiceAction.START, service_names)

        @service.command(help="Shuts down services.")
        @click.argument(
            "service_names",
            required=False,
            type=click.STRING,
            nargs=-1,
            callback=self._validate_service_names,
        )
        @click.pass_context
        def shutdown(ctx: Context, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_SHUTDOWN
            )
            self._action_orchestrator(ctx, ServiceAction.SHUTDOWN, service_names)

        @service.command(help="Stops services.", hidden=True)
        @click.argument(
            "service_names",
            required=False,
            type=click.STRING,
            nargs=-1,
            callback=self._validate_service_names,
        )
        @click.pass_context
        def stop(ctx: Context, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_SHUTDOWN
            )
            self._action_orchestrator(ctx, ServiceAction.SHUTDOWN, service_names)

        @service.command(help="Gets the status of services.")
        @click.argument(
            "service_names",
            required=False,
            type=click.STRING,
            nargs=-1,
            callback=self._validate_service_names,
        )
        @click.pass_context
        def status(ctx: Context, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_STATUS
            )
            self._action_orchestrator(ctx, ServiceAction.STATUS, service_names)

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
                cli_context: CliContext = ctx.obj
                cli_context.get_configuration_dir_state().verify_command_allowed(
                    AppcliCommand.ORCHESTRATOR
                )
                pass

            for command in orchestrator_commands:
                orchestrator.add_command(command)
            self.commands.update({"orchestrator": orchestrator})

    def _validate_service_names(
        self, ctx: click.Context, param: click.Option, values: click.Tuple
    ):
        """Validates service names. Exits with error if any invalid service names are passed in.

        Args:
            ctx (click.Context): Current CLI context.
            param (click.Option): The option parameter to validate.
            values (click.Tuple): The values passed to the option, could be multiple.
        """
        if not self.orchestrator.verify_service_names(ctx.obj, values):
            error_and_exit("One or more service names were not found.")
        return values

    def _action_orchestrator(
        self,
        ctx: Context,
        action: ServiceAction,
        service_names: tuple[str, ...] = None,
    ):
        """Applies an action to service(s).

        Args:
            ctx (Context): Click Context for current CLI.
            action (ServiceAction): action to apply to service(s), ie start, stop ...
            service_names (tuple[str, ...], optional): The name(s) of the service(s) to effect. If not provided the action applies to all services.
        """
        hooks = self.cli_configuration.hooks
        if action == ServiceAction.START:
            action_run_function = self.orchestrator.start
            pre_hook = hooks.pre_start
            post_hook = hooks.post_start

        elif action == ServiceAction.SHUTDOWN:
            action_run_function = self.orchestrator.shutdown
            pre_hook = hooks.pre_shutdown
            post_hook = hooks.post_shutdown

        elif action == ServiceAction.STATUS:
            action_run_function = self.orchestrator.status
            pre_hook = None
            post_hook = None

        else:
            error_and_exit(f"Unhandled action called: [{action.name}]")

        pre_run_log_message = (
            f"{action.name} "
            + (
                ", ".join(service_names)
                if service_names is not None and len(service_names) > 0
                else self.cli_configuration.app_name
            )
            + " ..."
        )
        post_run_log_message = f"{action.name} command finished with code [%i]"

        if pre_hook is not None:
            logger.debug(f"Running pre-{action.name} hook")
            pre_hook(ctx)

        logger.info(pre_run_log_message)
        result = action_run_function(ctx.obj, service_names)

        if post_hook is not None:
            logger.debug(f"Running post-{action.name} hook")
            post_hook(ctx, result)

        click.echo(result.stdout)
        logger.info(post_run_log_message, result.returncode)
        sys.exit(result.returncode)

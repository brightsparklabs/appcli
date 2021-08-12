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
from subprocess import CompletedProcess

# vendor libraries
import click
from click.core import Context

# local libraries
from appcli.commands.appcli_command import AppcliCommand
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
        START: Starts up a service
        SHUTDOWN: shutsdown a service
    """

    START = enum.auto()
    SHUTDOWN = enum.auto()


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
        @click.argument("service_names", required=False, type=click.STRING, nargs=-1)
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
            # At completion, the invoked command tries to exit the script, so we have to catch
            # the SystemExit.
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
            try:
                ctx.invoke(start, force=force, service_names=service_names)
            except SystemExit:
                pass

        @service.command(help="Starts services.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force start even if validation checks fail.",
        )
        @click.argument("service_names", required=False, type=click.STRING, nargs=-1)
        @click.pass_context
        def start(ctx: Context, force: bool, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_START, force
            )
            self.__action_orchestrator(ctx, ServiceAction.START, service_names, force)

        @service.command(help="Shuts down services.")
        @click.argument("service_names", required=False, type=click.STRING, nargs=-1)
        @click.pass_context
        def shutdown(ctx: Context, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_SHUTDOWN
            )
            self.__action_orchestrator(ctx, ServiceAction.SHUTDOWN, service_names)

        @service.command(help="Stops services.", hidden=True)
        @click.argument("service_names", required=False, type=click.STRING, nargs=-1)
        @click.pass_context
        def stop(ctx: Context, service_names: tuple[str, ...]):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.SERVICE_SHUTDOWN
            )
            self.__action_orchestrator(ctx, ServiceAction.SHUTDOWN, service_names)

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

    def __action_orchestrator(
        self,
        ctx: Context,
        action: ServiceAction,
        service_names: tuple[str, ...] = None,
        force: bool = False,
    ):
        """Applies an action to service(s)

        Args:
            ctx (Context): Click Context for current CLI.
            action (ServiceAction): action to apply to service(s), ie start, stop ...
            service_names (tuple[str, ...], optional): The name(s) of the service(s) to effect. If not provided the action applies to all services.
            force (bool, optional): If True, pass force to all subcommands. Defaults to False.
        """
        return_code = 0
        hooks = self.cli_configuration.hooks

        if action == ServiceAction.START:

            def pre_hook():
                if service_names:
                    services = ", ".join(service_names)
                else:
                    services = self.cli_configuration.app_name
                logger.debug("Running pre-start hook")
                hooks.pre_start(ctx)
                logger.info("Starting %s ...", services)

            def post_hook(result: CompletedProcess):
                logger.debug("Running post-start hook")

                hooks.post_start(ctx, result)
                logger.info(
                    "Start command finished with code [%i]",
                    result.returncode,
                )

            action_runner = self.orchestrator.start
        else:

            def pre_hook():
                if service_names:
                    services = ", ".join(service_names)
                else:
                    services = self.cli_configuration.app_name
                logger.debug("Running pre-shutdown hook")
                hooks.pre_shutdown(ctx)
                logger.info("Shutting down %s ...", services)

            def post_hook(result: CompletedProcess):
                logger.debug("Running post-shutdown hook")
                hooks.post_shutdown(ctx, result)
                logger.info(
                    "Shutdown command finished with code [%i]",
                    result.returncode,
                )

            action_runner = self.orchestrator.shutdown

        if service_names:
            if not self.orchestrator.verify_service_names(ctx.obj, service_names):
                sys.exit(1)
        else:
            service_names = None

        pre_hook()
        result = action_runner(ctx.obj, service_names)
        return_code = result.returncode
        post_hook(result)
        sys.exit(return_code)

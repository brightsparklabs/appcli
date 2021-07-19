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
from click.core import Context

# local libraries
from appcli.commands.appcli_command import AppcliCommand
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
        @click.argument("service_names", required=False, type=click.STRING,nargs=-1)
        @click.pass_context
        def restart(ctx, force, apply, service_names):
            """Restarts service(s)

            Args:
                ctx (Context): Click Context for current CLI.
                force (bool, optional): If True, pass force to all subcommands. Defaults to False.
                apply (bool, optional): If True, configure apply after service(s) are stopped. Defaults to False.
                service_name (str, optional): The name of the service to restart. If not provided, will restart all
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
        def start(ctx, force, service_names):
            if service_names:
                for service_name in service_names:
                    if not self.orchestrator.is_service(ctx.obj,service_name):
                        logger.error("No Such Service: %s", service_name)
                        sys.exit(1)
                for service_name in service_names:
                    returncode = self.__start(ctx, force, service_name)
                    if returncode:
                        sys.exit(returncode)
                sys.exit(0)
            else:
                returncode = self.__start(ctx, force, None)
                sys.exit(returncode)

        @service.command(help="Shuts down services.")
        @click.argument("service_names", required=False, type=click.STRING, nargs=-1)
        @click.pass_context
        def shutdown(ctx, service_names):
            if service_names:
                for service_name in service_names:
                    if not self.orchestrator.is_service(ctx.obj,service_name):
                        logger.error("No Such Service: %s",service_name)
                        sys.exit(1)
                for service_name in service_names:
                    returncode = self.__shutdown(ctx, service_name)
                    if returncode:
                        sys.exit(returncode)
                sys.exit(0)
            else:
                returncode = self.__shutdown(ctx, None)
                sys.exit(returncode)

        @service.command(help="Stops services.", hidden=True)
        @click.argument("service_names", required=False, type=click.STRING, nargs=-1)
        @click.pass_context
        def stop(ctx, service_names):
            if service_names:
                for service_name in service_names:
                    if not self.orchestrator.is_service(ctx.obj,service_name):
                        logger.error("No Such Service: %s",service_name)
                        sys.exit(1)
                for service_name in service_names:
                    returncode = self.__shutdown(ctx, service_name)
                    if returncode:
                        sys.exit(returncode)
                sys.exit(0)
            else:
                returncode = self.__shutdown(ctx, None)
                sys.exit(returncode)

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


    def __start(self, ctx: Context, force: bool, service_name: str = None) -> int:
        """Starts service(s) using the orchestrator.

        Args:
            ctx (Context): Click Context for current CLI.
            force (bool, optional): If True, forcibly shuts down service(s). Defaults to False.
            service_name (str, optional): The name of the service to shutdown. If not provided, will shut down all
                services.
        """

        cli_context: CliContext = ctx.obj
        cli_context.get_configuration_dir_state().verify_command_allowed(
            AppcliCommand.SERVICE_START, force
        )

        hooks = self.cli_configuration.hooks

        logger.debug("Running pre-start hook")
        hooks.pre_start(ctx)

        logger.info("Starting %s ...", self.cli_configuration.app_name)
        result = self.orchestrator.start(ctx.obj, service_name)

        logger.debug("Running post-start hook")
        hooks.post_start(ctx, result)

        logger.info("Start command finished with code [%i]", result.returncode)
        return result.returncode

    def __shutdown(self, ctx: Context, service_name: str = None) -> int:
        """Shutdown service(s) using the orchestrator.

        Args:
            ctx (Context): Click Context for current CLI.
            force (bool, optional): If True, forcibly shuts down service(s). Defaults to False.
            service_name (str, optional): The name of the service to shutdown. If not provided, will shut down all
                services.
        """
        cli_context: CliContext = ctx.obj
        cli_context.get_configuration_dir_state().verify_command_allowed(
            AppcliCommand.SERVICE_SHUTDOWN
        )

        hooks = self.cli_configuration.hooks

        logger.debug("Running pre-shutdown hook")
        hooks.pre_shutdown(ctx)

        logger.info("Shutting down %s ...", self.cli_configuration.app_name)
        result = self.orchestrator.shutdown(ctx.obj, service_name)

        logger.debug("Running post-shutdown hook")
        hooks.post_shutdown(ctx, result)

        logger.info("Shutdown command finished with code [%i]", result.returncode)
        return result.returncode

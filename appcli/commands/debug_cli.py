#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Common debug tasks.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import os
from pprint import pprint

# vendor libraries
import click

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.variables_manager import VariablesManager

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class DebugCli:
    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(
            hidden=True, invoke_without_command=True, help="Common debugging tasks."
        )
        @click.pass_context
        def debug(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @debug.command(
            help="Prints debug information about the current CLI context, configuration, and settings.",
        )
        @click.pass_context
        def info(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.DEBUG_INFO
            )
            variables_manager: VariablesManager = cli_context.get_variables_manager()

            print()
            print("=== CLI CONTEXT ===")
            pprint(cli_context)

            print()
            print("=== CONFIGURATION ===")
            pprint(self.cli_configuration)

            print()
            print("=== ORCHESTRATOR CONFIGURATION ===")
            pprint(vars(self.cli_configuration.orchestrator))

            print()
            print("=== VARIABLES ===")
            pprint(variables_manager.get_all_variables())

        @debug.command(
            help="Drops into a shell within the launcher for advanced debugging.",
        )
        @click.pass_context
        def shell(ctx):
            os.system("bash")

        # Expose the commands
        self.commands = {"debug": debug}

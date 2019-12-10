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
from appcli.logger import logger
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

        @click.command(
            help="Starts the system.\n\nOptionally specify CONTAINER to start only specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("container", nargs=-1, type=click.UNPROCESSED)
        def start(ctx, container):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(ctx)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.orchestrator.start(ctx.obj, container)

            logger.debug("Running post-start hook")
            hooks.post_start(ctx, result)

            sys.exit(result.returncode)

        @click.command(help="Stops the system.")
        @click.pass_context
        def stop(ctx):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-stop hook")
            hooks.pre_stop(ctx)

            logger.info("Stopping %s ...", configuration.app_name)
            result = self.orchestrator.stop(ctx.obj)

            logger.debug("Running post-stop hook")
            hooks.post_stop(ctx, result)

            sys.exit(result.returncode)

        @click.command(
            help="Streams the system logs.\n\nOptionally specify CONTAINER to only stream logs from specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("container", nargs=-1, type=click.UNPROCESSED)
        def logs(ctx, container):
            result = self.orchestrator.logs(ctx.obj, container)
            sys.exit(result.returncode)

        # NOTE: Hide the docker command as end users should not run it manually
        @click.command(
            hidden=True,
            help="Runs a specific docker compose/swarm command.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("command", nargs=-1, type=click.UNPROCESSED)
        def orchestrator_command(ctx, command):
            result = self.orchestrator.raw_command(ctx.obj, command)
            sys.exit(result.returncode)

        # expose the cli commands
        self.commands = {
            "start": start,
            "stop": stop,
            "logs": logs,
            "orchestrator_command": orchestrator_command,
        }

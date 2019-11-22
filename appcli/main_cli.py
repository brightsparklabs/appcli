#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The main (top-level) commands available when running the CLI.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import subprocess
import sys

# vendor libraries
import click

# internal libraries
from .logger import logger
from .models import CliContext, Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class MainCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        @click.command(
            help="Starts the system.\n\nOptionally specify CONTAINER to start only specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("container", nargs=-1, type=click.UNPROCESSED)
        def start(ctx, container):
            cli_context: CliContext = ctx.obj
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(cli_context)

            logger.info("Starting %s ...", configuration.app_name)
            result = __exec_command(ctx, ("up", "-d") + container)

            logger.debug("Running post-start hook")
            hooks.post_start(cli_context, result)

            sys.exit(result.returncode)

        @click.command(help="Stops the system.")
        @click.pass_context
        def stop(ctx):
            cli_context: CliContext = ctx.obj
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-stop hook")
            hooks.pre_stop(cli_context)

            logger.info("Stopping %s ...", configuration.app_name)
            result = __exec_command(ctx, ["down"])

            logger.debug("Running post-stop hook")
            hooks.post_stop(cli_context, result)

            sys.exit(result.returncode)

        @click.command(
            help="Streams the system logs.\n\nOptionally specify CONTAINER to only stream logs from specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("container", nargs=-1, type=click.UNPROCESSED)
        def logs(ctx, container):
            result = __exec_command(ctx, ("logs", "-f") + container)
            sys.exit(result.returncode)

        def __exec_command(ctx, subcommand):
            # The project-name of the docker-compose command is composed of project name and environment
            # so that multiple environments can run on a single machine without container naming conflicts
            cli_context: CliContext = ctx.obj
            PROJECT_NAME = f"{configuration.app_name}-{cli_context.environment}"
            docker_compose_command = [
                "docker-compose",
                "--project-name",
                PROJECT_NAME,
                "--file",
            ]
            command = docker_compose_command + [__get_compose_file_path(ctx)]
            command.extend(subcommand)
            logger.debug("Running [%s]", " ".join(command))
            result = subprocess.run(command)
            return result

        def __get_compose_file_path(ctx):
            cli_context: CliContext = ctx.obj
            return str(
                cli_context.generated_configuration_dir.joinpath(
                    "cli/docker-compose.yml"
                )
            )

        # expose the cli commands
        self.commands = {"start": start, "stop": stop, "logs": logs}

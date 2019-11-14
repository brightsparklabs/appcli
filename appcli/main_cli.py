#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The main (top-level) commands available when running the CLI.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import os
import subprocess
import sys
from typing import NamedTuple

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
        @click.command(
            help="Starts the system.\n\nOptionally specify CONTAINER to start only specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("container", nargs=-1, type=click.UNPROCESSED)
        def start(ctx, container):
            logger.info(f"Starting {configuration.app_name} ...")
            __run_and_exit(ctx, ("up", "-d") + container)

        @click.command(help="Stops the system.")
        @click.pass_context
        def stop(ctx):
            logger.info(f"Stopping {configuration.app_name} ...")
            __run_and_exit(ctx, ["down"])

        @click.command(
            help="Streams the system logs.\n\nOptionally specify CONTAINER to only stream logs from specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("container", nargs=-1, type=click.UNPROCESSED)
        def logs(ctx, container):
            __run_and_exit(ctx, ("logs", "-f") + container)

        def __run_and_exit(ctx, subcommand):
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
            logger.debug(f'Running [{" ".join(command)}]')
            my_env = os.environ
            my_env["COMPOSE_PROJECT_NAME"] = PROJECT_NAME
            result = subprocess.run(command, env=my_env)
            sys.exit(result.returncode)

        def __get_compose_file_path(ctx):
            cli_context: CliContext = ctx.obj
            return str(
                cli_context.generated_configuration_dir.joinpath(
                    "cli/docker-compose.yml"
                )
            )

        # expose the cli commands
        self.commands = {"start": start, "stop": stop, "logs": logs}

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
from pathlib import Path
from tempfile import NamedTemporaryFile

# vendor libraries
import click

# local libraries
from appcli.crypto import crypto
from appcli.logger import logger
from appcli.models import CliContext, Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class MainCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

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
            cli_context: CliContext = ctx.obj
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(cli_context)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.__exec_command(ctx, ("up", "-d") + container)

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
            result = self.__exec_command(ctx, ["down"])

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
            result = self.__exec_command(ctx, ("logs", "-f") + container)
            sys.exit(result.returncode)

        # expose the cli commands
        self.commands = {"start": start, "stop": stop, "logs": logs}

    # --------------------------------------------------------------------------
    # PRIVATE METHODS
    # --------------------------------------------------------------------------

    def __exec_command(self, ctx, subcommand):
        # The project-name of the docker-compose command is composed of project name and environment
        # so that multiple environments can run on a single machine without container naming conflicts
        cli_context: CliContext = ctx.obj
        PROJECT_NAME = f"{self.cli_configuration.app_name}-{cli_context.environment}"
        docker_compose_command = [
            "docker-compose",
            "--project-name",
            PROJECT_NAME,
            "--file",
        ]
        command = docker_compose_command + [str(self.__get_compose_file_path(ctx))]
        command.extend(subcommand)
        logger.debug("Running [%s]", " ".join(command))
        result = subprocess.run(command)
        return result

    def __get_compose_file_path(self, ctx) -> Path:
        cli_context: CliContext = ctx.obj
        compose_file: Path = cli_context.generated_configuration_dir.joinpath(
            "cli/docker-compose.yml"
        )

        key_file = cli_context.key_file
        if not key_file.is_file():
            logger.info("No decryption file found. Using docker-compose file as is.")
            return compose_file

        logger.info("Decrypting docker-compose file using [%s].", key_file)
        decrypted_compose_file: Path = Path(NamedTemporaryFile(delete=False).name)
        crypto.decrypt_values_in_file(compose_file, decrypted_compose_file, key_file)
        return decrypted_compose_file

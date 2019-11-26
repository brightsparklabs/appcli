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
from typing import List

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
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(ctx)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.__exec_command(ctx, ("up", "-d") + container)

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
            result = self.__exec_command(ctx, ["down"])

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
            result = self.__exec_command(ctx, ("logs", "-f") + container)
            sys.exit(result.returncode)

        # NOTE: Hide the compose command as end users should not run it manually
        @click.command(
            hidden=True,
            help="Runs a specific docker-compose command.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.pass_context
        @click.argument("command", nargs=-1, type=click.UNPROCESSED)
        def compose(ctx, command):
            result = self.__exec_command(ctx, command)
            sys.exit(result.returncode)

        # expose the cli commands
        self.commands = {"start": start, "stop": stop, "logs": logs, "compose": compose}

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
            str(self.__get_compose_file_path(ctx)),
        ]
        for path in self.__get_compose_override_file_paths(ctx):
            docker_compose_command = docker_compose_command + [
                "--file",
                str(path),
            ]

        docker_compose_command.extend(subcommand)
        logger.debug("Running [%s]", " ".join(docker_compose_command))
        result = subprocess.run(docker_compose_command)
        return result

    def __get_compose_file_path(self, ctx) -> Path:
        return self.__get_decrypted_generated_config_file(
            ctx, self.cli_configuration.docker_compose_file
        )

    def __get_compose_override_file_paths(self, ctx) -> List[Path]:
        return [
            self.__get_decrypted_generated_config_file(ctx, path)
            for path in self.cli_configuration.docker_compose_override_files
        ]

    def __get_decrypted_generated_config_file(self, ctx, relative_path: Path) -> Path:
        cli_context: CliContext = ctx.obj

        full_path: Path = cli_context.generated_configuration_dir.joinpath(
            relative_path
        )

        key_file = cli_context.key_file
        if not key_file.is_file():
            logger.info("No decryption file found. Using file as is.")
            return full_path

        logger.info("Decrypting file [%s] using [%s].", str(full_path), key_file)
        decrypted_file: Path = Path(NamedTemporaryFile(delete=False).name)
        crypto.decrypt_values_in_file(full_path, decrypted_file, key_file)
        return decrypted_file

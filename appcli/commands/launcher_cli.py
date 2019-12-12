#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The launcher command available when running the CLI.

Responsible for creating launcher commands.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import os

# vendor libraries
import click

# local libraries
from appcli.functions import check_valid_environment_variable_names
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class LauncherCli:

    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):

        self.configuration: Configuration = configuration

        @click.command(help="Outputs an appropriate launcher bash script to stdout")
        @click.option(
            "--launcher-env-var",
            "-e",
            help="Environment variables to set in the launcher command output. Can be specified multiple times.",
            nargs=2,
            type=click.Tuple([str, str]),
            multiple=True,
            callback=check_valid_environment_variable_names,
        )
        @click.pass_context
        def launcher(ctx, launcher_env_var):
            logger.info("Generating launcher script ...")
            cli_context: CliContext = ctx.obj
            APP_VERSION = os.environ.get("APP_VERSION", "latest")
            APP_NAME_UPPERCASE = configuration.app_name.upper()

            # Variables are defaulted in the script so that they can be overridden if desired
            print(
                f"""
#!/bin/bash

docker run \\
    --name osmosis_{cli_context.environment}_launcher_$(date +%s) \\
    --rm \\
    --interactive \\
    --tty \\"""
            )

            for name, value in launcher_env_var:
                print(f"    --env {name}='{value}' \\")

            print(
                f"""    --volume /var/run/docker.sock:/var/run/docker.sock \\
    {self.configuration.docker_image}:{APP_VERSION} \\
        --configuration-dir "${{{APP_NAME_UPPERCASE}_CONFIG_DIR:-{cli_context.configuration_dir}}}" \\
        --data-dir "${{{APP_NAME_UPPERCASE}_DATA_DIR:-{cli_context.data_dir}}}" \\
        --environment "${{{APP_NAME_UPPERCASE}_ENVIRONMENT:-{cli_context.environment}}}" \\"""
            )

            for name, path in cli_context.additional_data_dirs:
                print(f"        --additional-data-dir {name} '{path}' \\")
            for name, value in cli_context.additional_env_variables:
                print(f"        --additional-env-var {name} '{value}' \\")
            print("        $@")

        # expose the cli command
        self.commands = {"launcher": launcher}

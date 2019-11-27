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
from appcli.models import CliContext, Configuration

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
        @click.pass_context
        def launcher(ctx):

            cli_context: CliContext = ctx.obj
            APP_VERSION = os.environ.get("APP_VERSION")
            APP_NAME_UPPERCASE = configuration.app_name.upper()

            # Variables are defaulted in the script so that they can be overridden if desired
            print(
                f"""
#!/bin/bash

docker run \\
    --rm \\
    --volume /var/run/docker.sock:/var/run/docker.sock \\
    {self.configuration.docker_image}:{APP_VERSION} \\
        --configuration-dir "${{{APP_NAME_UPPERCASE}_CONFIG_DIR:-{cli_context.configuration_dir}}}" \\
        --data-dir "${{{APP_NAME_UPPERCASE}_DATA_DIR:-{cli_context.data_dir}}}" \\
        --environment "${{{APP_NAME_UPPERCASE}_ENVIRONMENT:-{cli_context.environment}}}" \\"""
            )

            for name, path in cli_context.additional_data_dirs:
                print(f"        --additional-data-dir {name} '{path}' \\")
            print("        $@")

        # expose the cli command
        self.commands = {"launcher": launcher}

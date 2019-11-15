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

# internal libraries
from .models import CliContext, Configuration

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

            # Variables are defaulted in the script so that they can be overridden if desired
            print(
                f"""
#!/bin/bash

mkdir -p "${{TELPASS_CONFIG_DIR:-{cli_context.configuration_dir}}}" "${{TELPASS_DATA_DIR:-{cli_context.data_dir}}}"

docker run \\
    --rm \\
    --volume /var/run/docker.sock:/var/run/docker.sock \\
    {self.configuration.docker_image}:{APP_VERSION} \\
        --configuration-dir "${{TELPASS_CONFIG_DIR:-{cli_context.configuration_dir}}}" \\
        --data-dir "${{TELPASS_DATA_DIR:-{cli_context.data_dir}}}" \\
        --environment "${{TELPASS_ENVIRONMENT:-{cli_context.environment}}}" \\
        $@
            """
            )

        # expose the cli command
        self.commands = {"launcher": launcher}


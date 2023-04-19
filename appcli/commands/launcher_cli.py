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
import datetime
import importlib.resources as pkg_resources
import os

# vendor libraries
import click
from jinja2 import StrictUndefined, Template

# local libraries
from appcli import templates
from appcli.commands.appcli_command import AppcliCommand
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

LAUNCHER_TEMPLATE_FILENAME = "launcher.j2"
""" The filename of the launcher template """

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class LauncherCli:
    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.configuration: Configuration = configuration

        @click.command(help="Outputs an appropriate launcher bash script to stdout.")
        @click.pass_context
        def launcher(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.LAUNCHER
            )

            logger.info("Generating launcher script ...")

            # Get the template from the appcli package
            launcher_template = pkg_resources.read_text(
                templates, LAUNCHER_TEMPLATE_FILENAME
            )
            logger.debug(f"Read template file [{LAUNCHER_TEMPLATE_FILENAME}]")

            render_variables = {
                "app_version": os.environ.get("APP_VERSION", "latest"),
                "app_name": configuration.app_name,
                "app_name_slug": configuration.app_name_slug,
                "cli_context": ctx.obj,
                "configuration": self.configuration,
                "current_datetime": f"{datetime.datetime.utcnow().isoformat()}+00:00",  # Since we're using utcnow(), we specify the offset manually
            }

            logger.debug(
                f"Rendering template with render variables: [{render_variables}]"
            )

            template = Template(
                launcher_template,
                undefined=StrictUndefined,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            try:
                output_text = template.render(render_variables)
                print(output_text)
            except Exception as e:
                error_and_exit(
                    f"Could not generate file from template. The configuration file is likely missing a setting: {e}"
                )

        # expose the CLI command
        self.commands = {"launcher": launcher}

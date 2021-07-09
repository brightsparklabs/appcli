#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The version command available when running the CLI.

Responsible for returning app version.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import click
import os

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class VersionCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):

        self.configuration: Configuration = configuration

        @click.command(help="Returns app version")
        def version():
            """Outputs the version of the app being managed with appcli
            """
            print(os.environ.get("APP_VERSION", "latest"))

        # expose the CLI command
        self.commands = {"version": version}

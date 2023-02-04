#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The version command available when running the CLI.

Responsible for fetching current app version.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import click

# standard libraries
from appcli.models.cli_context import CliContext

# local libraries
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

        @click.command(help="Fetches app version")
        @click.pass_context
        def version(ctx):
            """Fetches the version of the app being managed with appcli"""
            cli_context: CliContext = ctx.obj
            print(cli_context.app_version)

        # expose the CLI command
        self.commands = {"version": version}

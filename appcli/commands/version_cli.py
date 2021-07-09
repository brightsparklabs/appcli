#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The version command available when running the CLI.

Responsible for fetching current app version.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import os

# vendor libraries
import click

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
        def version():
            """Fetches the version of the app being managed with appcli"""
            print(os.environ.get("APP_VERSION", "latest"))

        # expose the CLI command
        self.commands = {"version": version}

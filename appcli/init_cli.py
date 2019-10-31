#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Initialises the system.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import click

# our library
from .models import Configuration
from .keycloak_manager import KeycloakManager

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class InitCli:
    def __init__(self, configuration: Configuration):
        self.app_name = configuration.app_name

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(invoke_without_command=True, help="Initialises the application.")
        @click.pass_context
        def init(ctx):
            if not ctx.invoked_subcommand is None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @init.command(
            help="Initialises a Keycloak instance with BSL-specific initial configuration"
        )
        @click.option(
            "--url",
            prompt="Url to Keycloak's auth API endpoint (e.g. http://localhost/auth/admin)",
        )
        @click.option("--username", prompt="Admin username")
        @click.option("--password", prompt="Admin password", hide_input=True)
        @click.pass_context
        def keycloak(ctx, url, username, password):
            keycloak = KeycloakManager(url, username, password)
            keycloak.configure_default(self.app_name)

        self.commands = {"init": init}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------


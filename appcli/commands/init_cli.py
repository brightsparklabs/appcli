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

# local libraries
from appcli.keycloak_manager import KeycloakManager
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class InitCli:
    def __init__(self, configuration: Configuration):
        self.app_name_slug = configuration.app_name_slug

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(invoke_without_command=True, help="Initialises the application.")
        @click.pass_context
        def init(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @init.command(
            help="Initialises a Keycloak instance with BSL-specific initial configuration."
        )
        @click.option(
            "--url",
            prompt="Url to Keycloak's auth API endpoint (e.g. http://localhost/auth/admin)",
        )
        @click.option("--username", prompt="Admin username")
        @click.option("--password", prompt="Admin password", hide_input=True)
        @click.option(
            "--insecure",
            "-k",
            is_flag=True,
            help="If supplied, allows insecure and unverified SSL connections to Keycloak.",
        )
        @click.pass_context
        def keycloak(ctx, url, username, password, insecure):
            keycloak = KeycloakManager(url, username, password, insecure=insecure)
            keycloak.configure_default(self.app_name_slug)

        self.commands = {"init": init}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

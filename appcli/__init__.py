#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Default package.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import os
import subprocess
import sys
from typing import NamedTuple

# vendor libraries
import click

# internal libraries
from .logger import logger, enable_debug_logging
from .models import Configuration
from .install_cli import InstallCli
from .main_cli import MainCli

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------

def create_cli(configuration: Configuration):

    @click.group(invoke_without_command=True, help='Manages the system')
    @click.option('--debug', '-d', help='Enables debug level logging', is_flag=True)
    @click.pass_context
    def cli(ctx, debug):
        if debug:
            enable_debug_logging()

        if ctx.obj is None:
            ctx.obj = configuration

        if not os.path.exists('/var/run/docker.sock'):
            logger.error(f'Please relaunch using:\n\n\tdocker run -v /var/run/docker.sock:/var/run/docker.sock {IMAGE_PREFIX} <command>')
            sys.exit(1)

        try:
            version = os.environ['APP_VERSION']
        except KeyError:
            logger.error('Could not determine version from environment variable [APP_VERSION]. This release is corrupt.')
            sys.exit(1)

        logger.info(f'Running {configuration.app_name} [v{version}]')

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            pass

    def run():
        cli(prog_name=configuration.app_name)

    install_command = InstallCli(configuration).command
    cli.add_command(install_command)

    main_commands = MainCli(configuration).commands
    for command in main_commands:
        cli.add_command(command)

    return run

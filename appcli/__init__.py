#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Default package.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import logging
import os
import subprocess
import sys
from typing import NamedTuple
from .models import *

# vendor libraries
import click
import coloredlogs

# internal libraries
from .configuration_manager import ConfigurationManager
from .configure_cli import ConfigureCli
from .install_cli import InstallCli
from .main_cli import MainCli
from .models import Configuration

# ------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------

FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logger = logging.getLogger(__name__)
coloredlogs.install(logger=logger, fmt=FORMAT)

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
            logger.setLevel(logging.DEBUG)

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

    # NOTE: Hide the command as end users should not run it manually
    @cli.command(hidden=True, help='Installs the system')
    @click.option('--overwrite', is_flag=True)
    def install(overwrite):
        installer = InstallCli(configuration)
        installer.install(overwrite)

    def run():
        cli(prog_name=configuration.app_name)

    main_commands = MainCli(configuration).commands
    for command in main_commands:
        cli.add_command(command)

    configure_command = ConfigureCli(configuration).command
    cli.add_command(configure_command)

    return run

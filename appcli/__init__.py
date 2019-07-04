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
from .models import Configuration
from .install_cli import InstallCli

# vendor libraries
import click
import coloredlogs

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
    @click.pass_context
    def cli(ctx):
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

    @cli.command(help='Starts the system')
    def start():
        command = 'docker-compose up -d'.split()
        result = subprocess.run(command)

    @cli.command(help='Stops the system')
    def stop():
        command = 'docker-compose down'.split()
        result = subprocess.run(command)

    # NOTE: Hide the command as end users should not run it manually
    @cli.command(hidden=True, help='Installs the system')
    @click.option('--overwrite', is_flag=True)
    def install(overwrite):
        installer = InstallCli(configuration)
        installer.install(overwrite)

    def run():
        cli(prog_name=configuration.app_name)

    return run

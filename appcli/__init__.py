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
import shlex
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

    # --------------------------------------------------------------------------
    # CREATE_CLI: CONSTANTS
    # --------------------------------------------------------------------------

    APP_NAME_UPPERCASE = configuration.app_name.upper()
    ENV_VAR_CONFIG_DIR = f'{APP_NAME_UPPERCASE}_CONFIG_DIR'
    ENV_VAR_DATA_DIR = f'{APP_NAME_UPPERCASE}_DATA_DIR'

    # --------------------------------------------------------------------------
    # CREATE_CLI: NESTED METHODS
    # --------------------------------------------------------------------------

    @click.group(invoke_without_command=True, help='Manages the system')
    @click.option('--debug', help='Enables debug level logging', is_flag=True)
    @click.option('--configuration-dir', '-c', help='Directory to read configuration files from', required=True)
    @click.option('--data-dir', '-d', help='Directory to store data to', required=True)
    @click.pass_context
    def cli(ctx, debug, configuration_dir, data_dir):
        if debug:
            logger.info("Enabling debug logging")
            coloredlogs.install(logger=logger, fmt=FORMAT, level=logging.DEBUG)
            logger.debug("Enabled debug logging")

        if ctx.obj is None:
            ctx.obj = {
                "appcli_configuration": configuration,
                "configuration_dir": configuration_dir,
                "data_dir": data_dir
            }
        else:
            logger.info("ctx was not defind")

        version = os.environ.get('APP_VERSION')
        if version is None:
            logger.error('Could not determine version from environment variable [APP_VERSION]. This release is corrupt.')
            sys.exit(1)

        check_docker_socket()
        relaunch_if_required(ctx)
        check_environment()

        logger.info(f'Running {APP_NAME_UPPERCASE} v{version}')
        logger.info(f'    {ENV_VAR_CONFIG_DIR}: [{configuration_dir}]')
        logger.info(f'    {ENV_VAR_DATA_DIR}:   [{data_dir}]')

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    # NOTE: Hide the command as end users should not run it manually
    @cli.command(hidden=True, help='Installs the system')
    @click.option('--overwrite', is_flag=True)
    def install(overwrite):
        installer = InstallCli(configuration)
        installer.install(overwrite)

    def run():
        cli(prog_name=configuration.app_name)

    def check_docker_socket():
        if not os.path.exists('/var/run/docker.sock'):
            error_msg=f'''Please relaunch using:

    docker run \
        -v /var/run/docker.sock:/var/run/docker.sock \
        {configuration.docker_image} \
            --configuration-dir <dir> COMMAND'
'''
            logger.error(error_msg)
            sys.exit(1)

    def relaunch_if_required(ctx):
        is_appcli_managed = os.environ.get('APPCLI_MANAGED')
        if is_appcli_managed is not None:
            # launched by appcli => no need to relaunch
            return

        # launched by user, not by appcli => need to launch via appcli
        configuration_dir = ctx.obj['configuration_dir']
        data_dir = ctx.obj['data_dir']
        command = shlex.split(f'''docker run
                        --volume /var/run/docker.sock:/var/run/docker.sock
                        --env APPCLI_MANAGED=Y
                        --env {ENV_VAR_CONFIG_DIR}='{configuration_dir}'
                        --volume '{configuration_dir}:{configuration_dir}'
                        --env {ENV_VAR_DATA_DIR}='{data_dir}'
                        --volume '{data_dir}:{data_dir}'
                        {configuration.docker_image}
                            --configuration-dir '{configuration_dir}'
                            --data-dir '{data_dir}'
            ''')
        if ctx.invoked_subcommand is not None:
            command.append(ctx.invoked_subcommand)
        logger.info("Relaunching with environment ...")
        logger.debug(f'Running [{" ".join(command)}]')
        result = subprocess.run(command)
        sys.exit(result.returncode)

    def check_environment():
        result = True
        mandatory_variables = [ENV_VAR_CONFIG_DIR, ENV_VAR_DATA_DIR]
        for env_variable in mandatory_variables:
            value = os.environ.get(env_variable)
            if value == None:
                logger.error(f'Mandatory environment variable is not defined [{env_variable}]')
                result = False
        if result == False:
            logger.error("Cannot run without all mandatory environment variables defined")
            sys.exit(1)

    # --------------------------------------------------------------------------
    # CREATE_CLI: LOGIC
    # --------------------------------------------------------------------------

    main_commands = MainCli(configuration).commands
    for command in main_commands:
        cli.add_command(command)

#    configure_command = ConfigureCli(configuration).command
#    cli.add_command(configure_command)

    return run

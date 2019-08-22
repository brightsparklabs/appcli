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
import shlex
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# vendor libraries
import click

# internal libraries
from .configuration_manager import ConfigurationManager
from .configure_cli import ConfigureCli
from .install_cli import InstallCli
from .logger import logger, enable_debug_logging
from .main_cli import MainCli
from .models import CliContext, Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------


def create_cli(configuration: Configuration):
    APP_NAME_UPPERCASE = configuration.app_name.upper()
    ENV_VAR_CONFIG_DIR = f'{APP_NAME_UPPERCASE}_CONFIG_DIR'
    ENV_VAR_GENERATED_CONFIG_DIR = f'{APP_NAME_UPPERCASE}_GENERATED_CONFIG_DIR'
    ENV_VAR_DATA_DIR = f'{APP_NAME_UPPERCASE}_DATA_DIR'

    # --------------------------------------------------------------------------
    # CREATE_CLI: NESTED METHODS
    # --------------------------------------------------------------------------

    @click.group(cls=ArgsGroup, invoke_without_command=True, help='Manages the system')
    @click.option('--debug', help='Enables debug level logging', is_flag=True)
    @click.option('--configuration-dir', '-c', help='Directory to read configuration files from', required=True, type=Path)
    @click.option('--data-dir', '-d', help='Directory to store data to', required=True, type=Path)
    @click.pass_context
    def cli(ctx, debug, configuration_dir, data_dir):
        if debug:
            logger.info("Enabling debug logging")
            enable_debug_logging()

        ctx.obj = CliContext(
            configuration_dir=configuration_dir,
            generated_configuration_dir=configuration_dir.joinpath(
                '.generated/conf'),
            data_dir=data_dir,
            subcommand_args=ctx.obj
        )

        version = os.environ.get('APP_VERSION')
        if version is None:
            logger.error(
                'Could not determine version from environment variable [APP_VERSION]. This release is corrupt.')
            sys.exit(1)

        check_docker_socket()
        relaunch_if_required(ctx)
        check_environment()

        logger.info(f'''{APP_NAME_UPPERCASE} v{version} CLI running with:
    {ENV_VAR_CONFIG_DIR}:           [{ctx.obj.configuration_dir}]
    {ENV_VAR_GENERATED_CONFIG_DIR}: [{ctx.obj.generated_configuration_dir}]
    {ENV_VAR_DATA_DIR}:             [{ctx.obj.data_dir}]''')

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    def run():
        cli(prog_name=configuration.app_name)

    def check_docker_socket():
        if not os.path.exists('/var/run/docker.sock'):
            error_msg = f'''Please relaunch using:

    docker run \
        -v /var/run/docker.sock:/var/run/docker.sock \
        {configuration.docker_image} \
            --configuration-dir <dir> \
            --data-dir <dir> COMMAND'
'''
            logger.error(error_msg)
            sys.exit(1)

    def relaunch_if_required(ctx):
        is_appcli_managed = os.environ.get('APPCLI_MANAGED')
        if is_appcli_managed is not None:
            # launched by appcli => no need to relaunch
            return

        # launched by user, not by appcli => need to launch via appcli
        cli_context: CliContext = ctx.ob
        configuration_dir = cli_context.configuration_dir
        generated_configuration_dir = cli_context.generated_configuration_dir
        data_dir = cli_context.data_dir
        command = shlex.split(f'''docker run
                        --volume /var/run/docker.sock:/var/run/docker.sock
                        --env APPCLI_MANAGED=Y
                        --env {ENV_VAR_CONFIG_DIR}='{configuration_dir}'
                        --volume '{configuration_dir}:{configuration_dir}'
                        --env {ENV_VAR_GENERATED_CONFIG_DIR}='{generated_configuration_dir}'
                        --volume '{generated_configuration_dir}:{generated_configuration_dir}'
                        --env {ENV_VAR_DATA_DIR}='{data_dir}'
                        --volume '{data_dir}:{data_dir}'
                        {configuration.docker_image}
                            --configuration-dir '{configuration_dir}'
                            --data-dir '{data_dir}'
            ''')
        if ctx.invoked_subcommand is not None:
            command.append(ctx.invoked_subcommand)
        if cli_context.subcommand_args is not None:
            command.extend(cli_context.subcommand_args)
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
                logger.error(
                    f'Mandatory environment variable is not defined [{env_variable}]')
                result = False
        if result == False:
            logger.error(
                "Cannot run without all mandatory environment variables defined")
            sys.exit(1)

    # --------------------------------------------------------------------------
    # CREATE_CLI: LOGIC
    # --------------------------------------------------------------------------

    install_command = InstallCli(configuration).command
    cli.add_command(install_command)

    main_commands = MainCli(configuration).commands
    for command in main_commands:
        cli.add_command(command)

    configure_command = ConfigureCli(configuration).command
    cli.add_command(configure_command)

    return run

# allow exposing subcommand arguments
# see: https://stackoverflow.com/a/44079245/3602961


class ArgsGroup(click.Group):
    def invoke(self, ctx):
        ctx.obj = tuple(ctx.args)
        super(ArgsGroup, self).invoke(ctx)

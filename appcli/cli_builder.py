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
from .configure_cli import ConfigureCli
from .init_cli import InitCli
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
    APP_NAME = configuration.app_name
    APP_NAME_UPPERCASE = APP_NAME.upper()
    ENV_VAR_CONFIG_DIR = f"{APP_NAME_UPPERCASE}_CONFIG_DIR"
    ENV_VAR_GENERATED_CONFIG_DIR = f"{APP_NAME_UPPERCASE}_GENERATED_CONFIG_DIR"
    ENV_VAR_DATA_DIR = f"{APP_NAME_UPPERCASE}_DATA_DIR"

    ENV_VAR_ENVIRONMENT = f"{APP_NAME_UPPERCASE}_ENVIRONMENT"
    APP_ENVIRONMENT = os.environ.get(ENV_VAR_ENVIRONMENT, "default")
    PROJECT_NAME = f"{APP_NAME}-{APP_ENVIRONMENT}"

    # --------------------------------------------------------------------------
    # CREATE_CLI: LOGIC
    # --------------------------------------------------------------------------

    install_commands = InstallCli(configuration).commands
    main_commands = MainCli(configuration, PROJECT_NAME).commands
    configure_commands = ConfigureCli(configuration).commands
    init_commands = InitCli(configuration).commands

    default_commands = {
        **configure_commands,
        **init_commands,
        **install_commands,
        **main_commands,
    }

    # --------------------------------------------------------------------------
    # CREATE_CLI: NESTED METHODS
    # --------------------------------------------------------------------------

    @click.group(
        cls=ArgsGroup, invoke_without_command=True, help=f"CLI for managing {APP_NAME}."
    )
    @click.option("--debug", help="Enables debug level logging.", is_flag=True)
    @click.option(
        "--configuration-dir",
        "-c",
        help="Directory to read configuration files from.",
        required=True,
        type=Path,
    )
    @click.option(
        "--data-dir", "-d", help="Directory to store data to.", required=True, type=Path
    )
    @click.pass_context
    def cli(ctx, debug, configuration_dir, data_dir):
        if debug:
            logger.info("Enabling debug logging")
            enable_debug_logging()

        ctx.obj = CliContext(
            configuration_dir=configuration_dir,
            data_dir=data_dir,
            subcommand_args=ctx.obj,
            generated_configuration_dir=configuration_dir.joinpath(".generated/conf"),
            app_configuration_file=configuration_dir.joinpath(f"{APP_NAME}.yml"),
            templates_dir=configuration_dir.joinpath("templates"),
            debug=debug,
            commands=default_commands,
        )

        version = os.environ.get("APP_VERSION")
        if version is None:
            logger.error(
                "Could not determine version from environment variable [APP_VERSION]. This release is corrupt."
            )
            sys.exit(1)

        check_docker_socket()
        relaunch_if_required(ctx)
        check_environment()

        logger.info(
            f"""{APP_NAME_UPPERCASE} v{version} CLI running with:
    {ENV_VAR_CONFIG_DIR}:           [{ctx.obj.configuration_dir}]
    {ENV_VAR_GENERATED_CONFIG_DIR}: [{ctx.obj.generated_configuration_dir}]
    {ENV_VAR_DATA_DIR}:             [{ctx.obj.data_dir}]
    {ENV_VAR_ENVIRONMENT}:          [{APP_ENVIRONMENT}]"""
        )

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    def run():
        cli(prog_name=configuration.app_name)

    def check_docker_socket():
        if not os.path.exists("/var/run/docker.sock"):
            error_msg = f"""Please relaunch using:

    docker run \\
        --rm
        --volume /var/run/docker.sock:/var/run/docker.sock \\
        {configuration.docker_image} \\
            --configuration-dir <dir> \\
            --data-dir <dir> COMMAND'
"""
            logger.error(error_msg)
            sys.exit(1)

    def relaunch_if_required(ctx):
        is_appcli_managed = os.environ.get("APPCLI_MANAGED")
        if is_appcli_managed is not None:
            # launched by appcli => no need to relaunch
            return

        # launched by user, not by appcli => need to launch via appcli
        cli_context: CliContext = ctx.obj
        configuration_dir = cli_context.configuration_dir
        generated_configuration_dir = cli_context.generated_configuration_dir
        data_dir = cli_context.data_dir
        command = shlex.split(
            f"""docker run
                        --rm
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
            """
        )
        if cli_context.debug:
            command.append("--debug")
        if ctx.invoked_subcommand is not None:
            command.append(ctx.invoked_subcommand)
        if cli_context.subcommand_args is not None:
            command.extend(cli_context.subcommand_args)
        logger.info("Relaunching with initialised environment ...")
        logger.debug("Running [%s]", " ".join(command))
        result = subprocess.run(command)
        sys.exit(result.returncode)

    def check_environment():
        result = True
        mandatory_variables = [ENV_VAR_CONFIG_DIR, ENV_VAR_DATA_DIR]
        for env_variable in mandatory_variables:
            value = os.environ.get(env_variable)
            if value is None:
                logger.error(
                    "Mandatory environment variable is not defined [%s]", env_variable
                )
                result = False
        if not result:
            logger.error(
                "Cannot run without all mandatory environment variables defined"
            )
            sys.exit(1)

    for command in default_commands.values():
        cli.add_command(command)

    for command in configuration.custom_commands:
        cli.add_command(command)

    return run


# allow exposing subcommand arguments
# see: https://stackoverflow.com/a/44079245/3602961
class ArgsGroup(click.Group):
    def invoke(self, ctx):
        ctx.obj = tuple(ctx.args)
        super(ArgsGroup, self).invoke(ctx)

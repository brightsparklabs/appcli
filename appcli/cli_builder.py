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
from math import floor
from pathlib import Path
from typing import Iterable
from time import time
from tabulate import tabulate

# vendor libraries
import click

# local libraries
from appcli.commands.configure_cli import ConfigureCli
from appcli.commands.encrypt_cli import EncryptCli
from appcli.commands.init_cli import InitCli
from appcli.commands.install_cli import InstallCli
from appcli.commands.launcher_cli import LauncherCli
from appcli.commands.main_cli import MainCli
from appcli.functions import extract_valid_environment_variable_names, error_and_exit
from appcli.logger import logger, enable_debug_logging
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = Path(__file__).parent

# ------------------------------------------------------------------------------
# PUBLIC METHODS
# ------------------------------------------------------------------------------


def create_cli(configuration: Configuration):
    """Build the CLI to be run

    Args:
        configuration (Configuration): the application's configuration settings
    """
    APP_NAME = configuration.app_name
    APP_NAME_UPPERCASE = APP_NAME.upper()
    ENV_VAR_CONFIG_DIR = f"{APP_NAME_UPPERCASE}_CONFIG_DIR"
    ENV_VAR_GENERATED_CONFIG_DIR = f"{APP_NAME_UPPERCASE}_GENERATED_CONFIG_DIR"
    ENV_VAR_DATA_DIR = f"{APP_NAME_UPPERCASE}_DATA_DIR"
    ENV_VAR_ENVIRONMENT = f"{APP_NAME_UPPERCASE}_ENVIRONMENT"

    APP_VERSION = os.environ.get("APP_VERSION", "latest")

    # --------------------------------------------------------------------------
    # CREATE_CLI: LOGIC
    # --------------------------------------------------------------------------

    default_commands = {}
    for cli_class in (
        ConfigureCli,
        EncryptCli,
        InitCli,
        InstallCli,
        LauncherCli,
        MainCli,
    ):
        commands = cli_class(configuration).commands
        default_commands.update(**commands)

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
    @click.option(
        "--environment",
        "-t",
        help="Environment to run, defaults to 'production'",
        required=False,
        type=click.STRING,
        default="production",
    )
    @click.option(
        "--additional-data-dir",
        "-a",
        help="Additional data directory to expose to launcher container. Can be specified multiple times.",
        type=str,
        multiple=True,
        callback=extract_valid_environment_variable_names,
    )
    @click.option(
        "--additional-env-var",
        "-e",
        help="Additional environment variables to expose to launcher container. Can be specified multiple times.",
        type=str,
        multiple=True,
        callback=extract_valid_environment_variable_names,
    )
    @click.pass_context
    def cli(
        ctx,
        debug,
        configuration_dir,
        data_dir,
        environment,
        additional_data_dir,
        additional_env_var,
    ):
        if debug:
            logger.info("Enabling debug logging")
            enable_debug_logging()

        ctx.obj = CliContext(
            configuration_dir=configuration_dir,
            data_dir=data_dir,
            additional_data_dirs=additional_data_dir,
            additional_env_variables=additional_env_var,
            environment=environment,
            subcommand_args=ctx.obj,
            debug=debug,
            key_file=Path(configuration_dir, "key"),
            generated_configuration_dir=configuration_dir.joinpath(".generated"),
            app_configuration_file=configuration_dir.joinpath(f"{APP_NAME}.yml"),
            templates_dir=configuration_dir.joinpath("templates"),
            project_name=f"{APP_NAME}_{environment}",
            app_version=APP_VERSION,
            commands=default_commands,
        )

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            sys.exit(1)

        # For the 'launcher' command, no further output/checks required.
        if ctx.invoked_subcommand == "launcher":
            # Don't execute this function any further, continue to run subcommand with the current cli context
            return

        check_docker_socket()
        relaunch_if_required(ctx)
        check_environment()

        # Table of configuration variables to print
        table = [
            [f"{ENV_VAR_CONFIG_DIR}", f"{ctx.obj.configuration_dir}"],
            [
                f"{ENV_VAR_GENERATED_CONFIG_DIR}",
                f"{ctx.obj.generated_configuration_dir}",
            ],
            [f"{ENV_VAR_DATA_DIR}", f"{ctx.obj.data_dir}"],
            [f"{ENV_VAR_ENVIRONMENT}", f"{ctx.obj.environment}"],
        ]

        # Print out the configuration values as an aligned table
        logger.info(
            "%s (version: %s) CLI running with:\n\n%s\n",
            APP_NAME_UPPERCASE,
            APP_VERSION,
            tabulate(table, colalign=("right",)),
        )
        if additional_data_dir:
            logger.info(
                "Additional data directories:\n\n%s\n",
                tabulate(
                    additional_data_dir,
                    headers=["Environment Variable", "Path"],
                    colalign=("right",),
                ),
            )
        if additional_env_var:
            logger.info(
                "Additional environment variables:\n\n%s\n",
                tabulate(
                    additional_env_var,
                    headers=["Environment Variable", "Value"],
                    colalign=("right",),
                ),
            )

    def run():
        """Run the entry-point click cli command
        """
        cli(prog_name=configuration.app_name)

    def check_docker_socket():
        """Check that the docker socket exists, and exit if it does not
        """
        if not os.path.exists("/var/run/docker.sock"):
            error_msg = f"""Please relaunch using:

    docker run \\
        --rm
        --volume /var/run/docker.sock:/var/run/docker.sock \\
        {configuration.docker_image}:{APP_VERSION} \\
            --configuration-dir <dir> \\
            --data-dir <dir> COMMAND'
            --environment <str>
"""
            error_and_exit(error_msg)

    def relaunch_if_required(ctx: click.Context):
        """Check if the appcli is being run within the context of the appcli container. If not, relaunch with appropriate
        environment variables and mounted volumes.

        Args:
            ctx (click.Context): The current cli context
        """
        is_appcli_managed = os.environ.get("APPCLI_MANAGED")
        if is_appcli_managed is not None:
            # launched by appcli => no need to relaunch
            return

        # launched by user, not by appcli => need to launch via appcli
        cli_context: CliContext = ctx.obj
        configuration_dir = cli_context.configuration_dir
        generated_configuration_dir = cli_context.generated_configuration_dir
        data_dir = cli_context.data_dir
        environment = cli_context.environment
        seconds_since_epoch = floor(time())
        command = shlex.split(
            f"""docker run
                        --name osmosis_{cli_context.environment}_relauncher_{seconds_since_epoch}
                        --interactive
                        --tty
                        --rm
                        --interactive
                        --tty
                        --volume /var/run/docker.sock:/var/run/docker.sock
                        --env APPCLI_MANAGED=Y
                        --env {ENV_VAR_CONFIG_DIR}='{configuration_dir}'
                        --volume '{configuration_dir}:{configuration_dir}'
                        --env {ENV_VAR_GENERATED_CONFIG_DIR}='{generated_configuration_dir}'
                        --volume '{generated_configuration_dir}:{generated_configuration_dir}'
                        --env {ENV_VAR_DATA_DIR}='{data_dir}'
                        --volume '{data_dir}:{data_dir}'
                        --env {ENV_VAR_ENVIRONMENT}='{environment}'
            """
        )

        for name, path in cli_context.additional_data_dirs:
            command.extend(
                shlex.split(
                    f"""
                        --env {name}="{path}"
                        --volume "{path}:{path}"
                    """
                )
            )

        for name, value in cli_context.additional_env_variables:
            command.extend(shlex.split(f"--env {name}=\"{value}\""))

        command.extend(
            shlex.split(
                f"""
                    {configuration.docker_image}:{APP_VERSION}
                    --configuration-dir "{configuration_dir}"
                    --data-dir "{data_dir}"
                    --environment "{environment}"
                """
            )
        )
        for name, path in cli_context.additional_data_dirs:
            command.extend(shlex.split(f"--additional-data-dir {name}=\"{path}\""))
        for name, value in cli_context.additional_env_variables:
            command.extend(shlex.split(f"--additional-env-var {name}=\"{value}\""))

        if cli_context.debug:
            command.append("--debug")
            # useful when debugging
            new_env = ""
            for i, value in enumerate(command):
                if value == "--env" and i + 1 < len(command):
                    new_env += f"\t{command[i+1]} \\\n"
            logger.debug(
                f"Relaunched environment will be initialised with:\n%s", new_env,
            )
        if ctx.invoked_subcommand is not None:
            command.append(ctx.invoked_subcommand)
        if cli_context.subcommand_args is not None:
            command.extend(cli_context.subcommand_args)

        logger.info("Relaunching with initialised environment ...")
        logger.debug("Running [%s]", " ".join(command))
        result = subprocess.run(command)
        sys.exit(result.returncode)

    def check_environment():
        """Confirm that mandatory environment variables and additional data directories are defined.
        """
        mandatory_variables = (ENV_VAR_CONFIG_DIR, ENV_VAR_DATA_DIR)
        check_environment_variable_defined(
            mandatory_variables,
            "Mandatory environment variable [%s] is not defined. [%s] should have been defined automatically by the CLI.",
            "Cannot run without all mandatory environment variables defined",
        )

        check_environment_variable_defined(
            configuration.mandatory_additional_env_variables,
            "Mandatory additional environment variable [%s] not defined. Please define with:\n\t--additional-env-var %s <value>",
            "Cannot run without all mandatory additional environment variables defined",
        )

        check_environment_variable_defined(
            configuration.mandatory_additional_data_dirs,
            "Mandatory additional data directory [%s] not defined. Please define with:\n\t--additional-data-dir %s </path/to/dir>",
            "Cannot run without all mandatory additional data directories defined",
        )

    def check_environment_variable_defined(
        env_variables: Iterable[str], error_message_template: str, exit_message: str
    ):
        """Check if environment variables are defined

        Args:
            env_variables (Iterable[str]): the environment variables to check
            error_message_template (str): a template for the error message
            exit_message (str): the exit message on error

        Returns:
            [type]: [description]
        """
        result = True
        for env_variable in env_variables:
            value = os.environ.get(env_variable)
            if value is None:
                logger.error(error_message_template, env_variable, env_variable)
                result = False
        if not result:
            error_and_exit(exit_message)

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

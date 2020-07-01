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
import sys
from pathlib import Path
from typing import Dict, Iterable

# vendor libraries
import click
from tabulate import tabulate

# local libraries
from appcli.commands.configure_cli import ConfigureCli
from appcli.commands.encrypt_cli import EncryptCli
from appcli.commands.init_cli import InitCli
from appcli.commands.install_cli import InstallCli
from appcli.commands.launcher_cli import LauncherCli
from appcli.commands.main_cli import MainCli
from appcli.commands.migrate_cli import MigrateCli
from appcli.functions import error_and_exit, extract_valid_environment_variable_names
from appcli.logger import enable_debug_logging, logger
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


def create_cli(configuration: Configuration, desired_environment: Dict[str, str] = {}):
    """Build the CLI to be run

    Args:
        configuration (Configuration): the application's configuration settings
    """
    APP_NAME = configuration.app_name.upper()
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
        MigrateCli,
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
            app_name=APP_NAME,
            app_version=APP_VERSION,
            commands=default_commands,
        )

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            sys.exit(1)

        # attempt to set desired environment
        initialised_environment = {}
        for k, v in desired_environment.items():
            if v is None:
                logger.warning("Environment variable [%s] has not been set", k)
            else:
                logger.debug("Exporting environment variable [%s]", k)
                os.environ[k] = v
                initialised_environment[k] = v
        if len(initialised_environment) != len(desired_environment):
            error_and_exit(
                "Could not set desired environment. Please ensure specified environment variables are set."
            )

        # For the 'launcher' command, no further output/checks required.
        if ctx.invoked_subcommand == "launcher":
            # Don't execute this function any further, continue to run subcommand with the current cli context
            return

        check_docker_socket()
        check_environment()

        # Table of configuration variables to print
        table = [
            ["Configuration directory", f"{ctx.obj.configuration_dir}"],
            [
                "Generated Configuration directory",
                f"{ctx.obj.get_generated_configuration_dir()}",
            ],
            ["Data directory", f"{ctx.obj.data_dir}"],
            ["Environment", f"{ctx.obj.environment}"],
        ]

        # Print out the configuration values as an aligned table
        logger.info(
            "%s (version: %s) CLI running with:\n\n%s\n",
            APP_NAME,
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
        cli(  # pylint: disable=no-value-for-parameter,unexpected-keyword-arg
            prog_name=configuration.app_name
        )

    def check_docker_socket():
        """Check that the docker socket exists, and exit if it does not
        """
        if not os.path.exists("/var/run/docker.sock"):
            error_msg = """Docker socket not present. Please launch with a mounted /var/run/docker.sock"""
            error_and_exit(error_msg)

    def check_environment():
        """Confirm that mandatory environment variables and additional data directories are defined.
        """

        ENV_VAR_CONFIG_DIR = f"{APP_NAME}_CONFIG_DIR"
        ENV_VAR_GENERATED_CONFIG_DIR = f"{APP_NAME}_GENERATED_CONFIG_DIR"
        ENV_VAR_DATA_DIR = f"{APP_NAME}_DATA_DIR"
        ENV_VAR_ENVIRONMENT = f"{APP_NAME}_ENVIRONMENT"
        launcher_set_mandatory_env_vars = [
            ENV_VAR_CONFIG_DIR,
            ENV_VAR_GENERATED_CONFIG_DIR,
            ENV_VAR_DATA_DIR,
            ENV_VAR_ENVIRONMENT,
        ]

        launcher_env_vars_set = check_environment_variable_defined(
            launcher_set_mandatory_env_vars,
            "Mandatory environment variable [%s] not defined. This should be set within the script generated with the 'launcher' command.",
            "Cannot run without all mandatory environment variables defined",
        )

        additional_env_vars_set = check_environment_variable_defined(
            configuration.mandatory_additional_env_variables,
            'Mandatory additional environment variable [%s] not defined. When running the \'launcher\' command, define with:\n\t--additional-env-var "%s"="<value>"',
            "Cannot run without all mandatory additional environment variables defined",
        )

        additional_data_dir_env_vars_set = check_environment_variable_defined(
            configuration.mandatory_additional_data_dirs,
            'Mandatory additional data directory [%s] not defined. When running the \'launcher\' command, define with:\n\t--additional-data-dir "%s"="</path/to/dir>"',
            "Cannot run without all mandatory additional data directories defined",
        )

        if not (
            launcher_env_vars_set
            and additional_env_vars_set
            and additional_data_dir_env_vars_set
        ):
            error_and_exit(
                "Some mandatory environment variables weren't set. See error messages above."
            )
        logger.info("All required environment variables are set.")

    def check_environment_variable_defined(
        env_variables: Iterable[str], error_message_template: str, exit_message: str
    ) -> bool:
        """Check if environment variables are defined

        Args:
            env_variables (Iterable[str]): the environment variables to check
            error_message_template (str): a template for the error message
            exit_message (str): the exit message on error

        Returns:
            [bool]: True if all environment variables are defined, otherwise False.
        """
        result = True
        for env_variable in env_variables:
            value = os.environ.get(env_variable)
            if value is None:
                logger.error(error_message_template, env_variable, env_variable)
                result = False
            else:
                logger.debug(
                    f"Confirmed environment variable is set - '{env_variable}' = '{value}'"
                )
        if not result:
            logger.error(exit_message)

        return result

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

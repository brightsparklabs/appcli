#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for backup and restoration of application configuration and data.

Responsible for creating local backups, remote (offsite) backups and restoring from a local backup.
Pulls configuration from `stack-settings.yml`.
If no `backup` section is present in the configuration, a local backup is still taken with nothing excluded and rolling
backup deletion disabled.
See the README for further details on backup configuration.
_______________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import click

# local libraries
from appcli.backup_manager.backup_manager import BackupManager
from appcli.commands.appcli_command import AppcliCommand
from appcli.configuration_manager import ConfigurationManager
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------1------------------------------------------------------------

# The name of the key for the backup block in the stack settings file.
BACKUP = "backups"

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class BackupManagerCli:
    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        # ------------------------------------------------------------------------------
        # PUBLIC METHODS
        # ------------------------------------------------------------------------------

        @click.command(
            help="Create a backup of application data and configuration. Will also execute any configured remote strategies."
        )
        @click.option(
            "--pre-stop-services/--no-pre-stop-services",
            default=True,
            is_flag=True,
            help="Whether to stop services BEFORE the backup is executed. Defaults to stop services.",
        )
        @click.option(
            "--post-start-services/--no-post-start-services",
            default=True,
            is_flag=True,
            help="Whether to start services AFTER the backup is complete. Default to start services.",
        )
        @click.argument("backup_name", type=click.STRING, required=False)
        @click.pass_context
        def backup(ctx, pre_stop_services, post_start_services, backup_name):
            cli_context: CliContext = ctx.obj

            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.BACKUP
            )

            try:
                services_cli = cli_context.commands["service"]
            except KeyError:
                # The `service` command is not available, which means the orchestrator has no services to manage.
                # Therefore there are no services to stop.
                logger.info("No services to stop.")
                services_cli = None
                pre_stop_services = False
                post_start_services = False

            if pre_stop_services:
                logger.info("Stopping application services ...")
                try:
                    ctx.invoke(services_cli.commands["shutdown"])
                except SystemExit:
                    # At completion, the invoked command tries to exit the script, so we have to catch
                    # the SystemExit.
                    pass

            backup_manager: BackupManager = self.__create_backup_manager(cli_context)
            backup_manager.backup(ctx, backup_name=backup_name)

            if post_start_services:
                logger.info("Starting application services ...")
                try:
                    ctx.invoke(services_cli.commands["start"])
                except SystemExit:
                    # At completion, the invoked command tries to exit the script, so we have to catch
                    # the SystemExit.
                    pass

            if pre_stop_services and not post_start_services:
                logger.warn(
                    "Services have been shutdown by the backup command and were intentionally not restarted."
                )

        @click.command(help="Restore a backup of application data and configuration.")
        @click.option(
            "--pre-stop-services/--no-pre-stop-services",
            default=True,
            is_flag=True,
            help="Whether to stop services BEFORE the restore is executed. Defaults to stop services.",
        )
        @click.option(
            "--post-start-services/--no-post-start-services",
            default=True,
            is_flag=True,
            help="Whether to start services AFTER the restore is complete. Default to start services.",
        )
        @click.option(
            "--force",
            is_flag=True,
            help="Force restoring a backup even if validation checks fail.",
        )
        @click.argument("backup_file")
        @click.pass_context
        def restore(ctx, pre_stop_services, post_start_services, force, backup_file):
            cli_context: CliContext = ctx.obj

            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.RESTORE, force
            )

            backup_manager: BackupManager = self.__create_backup_manager(cli_context)

            # Ensure the backup file exists before attempting restore
            if not backup_manager.backup_file_exists(ctx, backup_file):
                error_and_exit(f"Backup file [{backup_file}] not found.")

            try:
                services_cli = cli_context.commands["service"]
            except KeyError:
                # The `service` command is not available, which means the orchestrator has no services to manage.
                # Therefore there are no services to stop.
                logger.info("No services to stop.")
                services_cli = None
                pre_stop_services = False
                post_start_services = False

            if pre_stop_services:
                logger.info("Stopping application services ...")
                try:
                    ctx.invoke(services_cli.commands["shutdown"])
                except SystemExit:
                    # At completion, the invoked command tries to exit the script, so we have to catch
                    # the SystemExit.
                    pass

            backup_manager.restore(ctx, backup_file)

            if post_start_services:
                logger.info("Starting application services ...")
                try:
                    ctx.invoke(services_cli.commands["start"])
                except SystemExit:
                    # At completion, the invoked command tries to exit the script, so we have to catch
                    # the SystemExit.
                    pass

            if pre_stop_services and not post_start_services:
                logger.warn(
                    "Services have been shutdown by the restore command and were intentionally not restarted."
                )

        @click.command(help="View a list of available backups.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force viewing backups even if validation checks fail.",
        )
        @click.pass_context
        def view_backups(ctx, force):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.VIEW_BACKUPS, force
            )

            backup_manager: BackupManager = self.__create_backup_manager(cli_context)

            backup_manager.view_backups(ctx)

        # Expose the commands.
        self.commands = {
            "backup": backup,
            "restore": restore,
            "view_backups": view_backups,
        }

    def __create_backup_manager(self, cli_context: CliContext) -> BackupManager:
        """
        Create a BackupManager object from the `backup` section of the stack settings configuration file.

        Returns:
            A BackupManager object that contains backup configuration.
        """
        # Get the settings from the `stack-settings` file.
        configuration = ConfigurationManager(cli_context, self.cli_configuration)
        try:
            stack_variables = configuration.get_stack_variable(BACKUP)
        except (KeyError, TypeError) as e:
            error_and_exit(f"No backup key found in stack settings. [{e}]")

        if stack_variables is None:
            error_and_exit("Backup key in stack settings was empty.")

        # Create our BackupManager from the settings.
        return BackupManager(stack_variables)

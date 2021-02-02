#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for backup and restoration of application configuration and data.

Responsible for creating local backups, remote (offsite) backups and restoring from a local backup.
Pulls configuration from `stack-settings.yml`
_______________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import click

from appcli.backup_manager.backup_manager import BackupManager, RemoteStrategyFactory
from appcli.configuration_manager import ConfigurationManager

# local libraries
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

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

        @click.command(help="Create a backup of application data and configuration.")
        @click.pass_context
        def backup(ctx):
            hooks = self.cli_configuration.hooks

            hooks.pre_backup(ctx)

            """
            TODO:


            Decrypt stack-settings.yml

            commit stack-settings.yml file to teraflow

            Update readme

            """

            cli_context: CliContext = ctx.obj
            key_file = cli_context.get_key_file()

            backup_manager = self.__create_backup_manager(cli_context)

            # Create a local backup
            backup_filename = backup_manager.backup(ctx)

            # Get any remote backup strategies.
            remote_strategies = RemoteStrategyFactory.get_strategy(
                backup_manager, key_file
            )

            # Execute each of the remote backup strategies with the local backup file.
            for backup_strategy in remote_strategies:
                backup_strategy.backup(backup_filename)

            hooks.post_backup(ctx, backup_filename)

        @click.command(help="Restore a backup of application data and configuration.")
        @click.argument("backup_file")
        @click.pass_context
        def restore(ctx, backup_file):
            hooks = self.cli_configuration.hooks

            hooks.pre_restore(ctx, backup_file)

            cli_context: CliContext = ctx.obj

            backup_manager = self.__create_backup_manager(cli_context)
            backup_manager.restore(ctx, backup_file)

            hooks.post_restore(ctx, backup_file)

        @click.command(help="View a list of available backups.")
        @click.pass_context
        def view_backups(ctx):
            hooks = self.cli_configuration.hooks

            cli_context: CliContext = ctx.obj

            backup_manager = self.__create_backup_manager(cli_context)
            backup_manager.view_backups(ctx)

            hooks.view_backups(ctx)

        # Expose the commands
        self.commands = {
            "backup": backup,
            "restore": restore,
            "view_backups": view_backups,
        }

    def __create_backup_manager(self, cli_context):
        # Get the settings from the `stack-settings` file
        configuration = ConfigurationManager(cli_context, self.cli_configuration)
        stack_variables_manager = configuration.get_stack_variables_manager()
        stack_variables = stack_variables_manager.get_all_variables()

        # Create our BackupManager from the settings
        return BackupManager(stack_variables)

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

# standard libraries
import sys
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path


# vendor libraries
import click
from click.core import Context


# local libraries
from appcli.functions import execute_validation_functions
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.configuration_manager import ConfigurationManager
from appcli.backup_manager.backup_manager import RemoteStrategyFactory, BackupManager



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

            Handle when stack-settings is not present

            Decrypt stack-settings.yml 
                See Call crypto.decrypt
                and orchestrators.decrypt_file
                -cypher error

            commit stack-settings.yml file to teraflow

            Implement frequency logic (similar to cron)

            Comments everywhere

            Update readme

            Better handling of invalid strategy

            Linting

            """

            cli_context: CliContext = ctx.obj
            key_file = cli_context.get_key_file()

            # Get settings value and print
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            stack_variables_manager = configuration.get_stack_variables_manager()


            stack_variables = stack_variables_manager.get_all_variables()

            backup_manager = BackupManager(stack_variables)

            backup_filename = backup_manager.backup(ctx)

            remote_strategies = RemoteStrategyFactory.get_strategy(stack_variables['backup'], key_file)

            #for backup_strategy in remote_strategies:
            #    backup_strategy.backup(backup_filename)

            hooks.post_backup(ctx, backup_filename)

        @click.command(help="Restore a backup of application data and configuration.")
        @click.argument("backup_file")
        @click.pass_context
        def restore(ctx, backup_file):
            hooks = self.cli_configuration.hooks

            hooks.pre_restore(ctx, backup_file)


            cli_context: CliContext = ctx.obj

            key_file = cli_context.get_key_file()


            # Get settings value and print
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            stack_variables_manager = configuration.get_stack_variables_manager()


            stack_variables = stack_variables_manager.get_all_variables()


            backup_manager = BackupManager(stack_variables)
            backup_manager.restore(ctx, backup_file)

            hooks.post_restore(ctx, backup_file)

        @click.command(help="View a list of available backups.")
        @click.pass_context
        def view_backups(ctx):
            hooks = self.cli_configuration.hooks

            cli_context: CliContext = ctx.obj

            key_file = cli_context.get_key_file()

            # Get settings value and print
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            stack_variables_manager = configuration.get_stack_variables_manager()


            stack_variables = stack_variables_manager.get_all_variables()

            backup_manager = BackupManager(stack_variables)
            backup_manager.view_backups(ctx)

            hooks.view_backups(ctx)
        

        # Expose the commands
        self.commands = {
            "backup":backup,
            "restore":restore,
            "view_backups":view_backups
        }



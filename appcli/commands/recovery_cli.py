#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for lifecycle management of application services.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import sys
from datetime import datetime, timedelta, timezone
import os
import tarfile
from pathlib import Path

# vendor libraries
import click
from click.core import Context
import dateutil.parser

from appcli.configuration_manager import (
    confirm_generated_config_dir_exists,
    confirm_generated_configuration_is_using_current_configuration,
)

# local libraries
from appcli.functions import execute_validation_functions
from appcli.git_repositories.git_repositories import (
    confirm_config_dir_exists_and_is_not_dirty,
    confirm_config_version_matches_app_version,
    confirm_generated_config_dir_exists_and_is_not_dirty,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class RecoveryCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):

        self.cli_configuration: Configuration = configuration

        # ------------------------------------------------------------------------------
        # PUBLIC METHODS
        # ------------------------------------------------------------------------------

        @click.group(
            invoke_without_command=True, help="Backup or restore the Teraflow application."
        )
        @click.pass_context
        def recovery(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return
            click.echo(ctx.get_help())

        @recovery.command(help="Create a backup of application data and configuration.")
        @click.pass_context
        def backup(ctx):
            self.__backup(ctx)

        @recovery.command(help="Restore a backup of application data and configuration.")
        @click.argument("backup")
        @click.pass_context
        def restore(ctx, template):


        @recovery.command(help="View a list of available backups.")
        @click.pass_context
        def view(ctx):
            self.__view_backups(ctx)



        # Expose the commands
        self.commands = {
            "recovery":recovery
        }

    def __restore(self, ctx):
        cli_context: appcli.CliContext = ctx.obj
        logger.info("Initiating system restore")

        #prompt user to confirm "yes" to continue

        #Stop system

        #delete conf + data dirs

        #extract tar to root 'production' folder

        #start system


    def __backup(self, ctx):
        cli_context: appcli.CliContext = ctx.obj
        logger.info("Initiating system backup")

        #logger.info("Stopping system ...")


        #try:
        #    ctx.invoke(cli_context.commands["service shutdown"])
        #except SystemExit:
            # At completion, the invoked command tries to exit the script, so we have to catch
            # the SystemExit
        #    pass


        backup_dir: Path = cli_context.backup_dir
        data_dir: Path = cli_context.data_dir
        conf_dir: Path = cli_context.configuration_dir
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        backup_name: Path = os.path.join(backup_dir, self.__create_backup_filename())


        logger.info(f"Creating backup {backup_name}")
        #check to see if backup directory exists
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # We want to keep at least the last 7 backups.
        # Covers off the case where we 'lose' the stack for a week, then get it back and on the next
        # backup potentially delete all the previous backups.
        # Simply sort in Chronological descending order, and then delete from the appropriate index
        # onward.
        number_of_backups_to_retain = 6
        logger.info(f"Removing old backups - retaining at least the last [{number_of_backups_to_retain}] backups ...")

        backup_dir_files = sorted(os.listdir(backup_dir), key=self.__parse_datetime_from_filename, reverse=True)
        backups_to_delete = backup_dir_files[number_of_backups_to_retain:]
        for backup_to_delete in backups_to_delete:
            backup_file: Path = Path(os.path.join(backup_dir, backup_to_delete))
            logger.info(f"Deleting backup file [{backup_file}]")
            os.remove(backup_file)

        
        logger.info("Taking backup ...")
        with tarfile.open(backup_name, "w:gz") as tar:
            logger.info(f"Backing up [{data_dir}] ...")
            tar.add(data_dir, arcname=os.path.basename(data_dir))

            logger.info(f"Backing up [{conf_dir}] ...")
            tar.add(conf_dir, arcname=os.path.basename(conf_dir))


        logger.info("Backup completed")
        #logger.info("Starting system ...")
        # At end of script so do not care about SystemExit
        #ctx.invoke(cli_context.commands["service start"])


    def __view_backups(self, ctx):
        """Private function that displays a list of available backups that were found in the backup folder

        """
        cli_context: appcli.CliContext = ctx.obj
        logger.info("Displaying all available backups.")

        backup_dir: Path = cli_context.backup_dir

        backup_dir_files = sorted(os.listdir(backup_dir), key=self.__parse_datetime_from_filename, reverse=True)
        for backup in backup_dir_files:
            logger.info(backup)


    def __create_backup_filename(self):
        """Private function that returns the filename of the backup .tgz file
           Format is "<APP_NAME>_<datetime.now>.tgz"

        Returns:
            The formatted .tgz filename
        """
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        return f"{self.cli_configuration.app_name.upper()}_{now.isoformat()}.tgz"
        
    def __parse_datetime_from_filename(self, filename):
        """Private function to parse a datetime object from a filename.

        Args:
            filename (string): The filename to parse.

        Returns:
            The datetime object.
        """

        # Filename is <app_name>_<date>.tgz, need to strip the app_name and file extension.
        timestamp = Path(filename).stem.replace(self.cli_configuration.app_name.upper() + "_", '')

        # Filename may not be in the expected format, in that case assign it a sort value of now
        # so it appears at the top of the list.
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        sort_key = now.isoformat()

        try: 
            return dateutil.parser.parse(timestamp)
        except ValueError:
            logger.info(f"Unexpected backup found {filename}")

        return dateutil.parser.parse(sort_key)

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for backup and restoration of application configuration and data.
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
import shutil


# vendor libraries
import click
from click.core import Context
import dateutil.parser


# local libraries
from appcli.functions import execute_validation_functions
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.configuration_manager import ConfigurationManager
from appcli.backup_manager.backup_manager import RemoteStrategyFactory



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

            Move localbackup from this file into backup_manager.py

            Add tags to s3 strategy

            commit stack-settings.yml file to teraflow

            Implement glob ignore list

            Implement frequency logic (similar to cron)

            Comments everywhere

            Update readme

            Better handling of invalid strategy

            """

            backup_filename = self.__backup(ctx)
            hooks.post_backup(ctx, backup_filename)

        @click.command(help="Restore a backup of application data and configuration.")
        @click.argument("backup_file")
        @click.pass_context
        def restore(ctx, backup_file):
            hooks = self.cli_configuration.hooks

            hooks.pre_restore(ctx, backup_file)
            self.__restore(ctx, backup_file)
            hooks.post_restore(ctx, backup_file)

        @click.command(help="View a list of available backups.")
        @click.pass_context
        def view_backups(ctx):
            hooks = self.cli_configuration.hooks

            self.__view_backups(ctx)
            hooks.view_backups(ctx)

        @click.command(help="View a list of available backups.")
        @click.pass_context
        def remote_backup(ctx):
            cli_context: CliContext = ctx.obj

            # Get settings value and print
            configuration = ConfigurationManager(cli_context, self.cli_configuration)
            stack_variables_manager = configuration.get_stack_variables_manager()

            backup_filename = self.__backup(ctx)


            stack_variables = stack_variables_manager.get_all_variables()

            remote_strategies = RemoteStrategyFactory.get_strategy(stack_variables['backup'])

            for backup_strategy in remote_strategies:
                backup_strategy.backup(backup_filename)

        

        # Expose the commands
        self.commands = {
            "backup":backup,
            "restore":restore,
            "view_backups":view_backups,
            "remote_backup":remote_backup
        }

    def __restore(self, ctx, backup_filename):
        """Restore application data and configuration from the provided backup `.tgz` file.
        This will create a backup of the existing data and config, remove the contents `conf`, `data` and `conf/.generated`. 
        Each of these folders is mapped into appcli which means we keep the folder but replace their contents with out backup.

        Args:
            backup_filename (string): The name of the file to use in restoring data. The path of the file will be pulled from `CliContext.obj.backup_dir`.
        """
        cli_context: appcli.CliContext = ctx.obj

        backup_dir: Path = cli_context.backup_dir
        data_dir: Path = cli_context.data_dir
        conf_dir: Path = cli_context.configuration_dir
        generated_conf_dir: Path = cli_context.get_generated_configuration_dir()
        backup_name: Path = Path(os.path.join(backup_dir, backup_filename))

        logger.info("Initiating system restore")

        # Check that the backup file exists.
        if not backup_name.is_file():
            logger.error(f"Backup file {backup_name} not found.")
            return

        # Stop the system.
        logger.info("Stopping system ...")
        services_cli = cli_context.commands["service"]
        try:
           ctx.invoke(services_cli.commands["shutdown"])
        except SystemExit:
            # At completion, the invoked command tries to exit the script, so we have to catch
            # the SystemExit
            pass

        # Perform a backup of the existing application config and data.
        logger.info("Creating backup of existing application data and configuration")
        restore_backup_name = self.__backup(ctx)
        logger.info(f"Backup generated before restore was: {restore_backup_name}")

        # Clear the existing folders that will be populated from the backup
        # Each of these is mounted, deleting them may result in "Device or resource busy"
        # so we clear their contents instead.
        # Clear the `data` directory. 
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f"Failed to delete {file_path}. Reason: {e}")

        # Clear the `conf` directory while ignoring `conf/.generated`.
        for filename in os.listdir(conf_dir):
            file_path = os.path.join(conf_dir, filename)
            try:
                if str(generated_conf_dir) in file_path:
                    # We have the .generated sub folder, handle it seperately. 
                    pass
                elif os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f"Failed to delete {file_path}. Reason: {e}")

        # Clear the `conf/.generated` directory.
        for filename in os.listdir(generated_conf_dir):
            file_path = os.path.join(generated_conf_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error('Failed to delete %s. Reason: %s' % (file_path, e))

        # Extract conf and data directories from the tar.
        try:
            with tarfile.open(backup_name) as tar:
                tar.extractall(conf_dir, members=self.__members(tar, "conf/"))
                tar.extractall(data_dir, members=self.__members(tar, "data/"))
        
        except Exception as e:
            logger.error(f"Failed to extract backup - {e}")

        logger.info("Restore complete.")


    def __members(self, tf, subfolder):
        """Helper function for extracting folders from a tar ball. 
        Will allow extracting files to exclude the provided subfolder from their extracted path.

        Args:
            tf (tar): The tar file to extract.
            subfolder (string): The subfolder to exclude from the extraction path.
        """
        length_of_subfolder = len(subfolder)
        for member in tf.getmembers():
            if member.path.startswith(subfolder):
                member.path = member.path[length_of_subfolder:]
                yield member

    

    def __backup(self, ctx):
        """Create a backup `.tgz` file that contains application data and configuration.
        Will shutdown the application and generate a backup containing CliContext.obj.data_dir and CliContext.obj.configuration_dir.

        Returns:
            backup_name (string): The filename of the generated backup that includes the full path.
        """
        cli_context: appcli.CliContext = ctx.obj
        logger.info("Initiating system backup")

        logger.info("Stopping system ...")
        services_cli = cli_context.commands["service"]
        try:
           ctx.invoke(services_cli.commands["shutdown"])
        except SystemExit:
            # At completion, the invoked command tries to exit the script, so we have to catch
            # the SystemExit
            pass

        backup_dir: Path = cli_context.backup_dir
        data_dir: Path = cli_context.data_dir
        conf_dir: Path = cli_context.configuration_dir
        backup_name: Path = os.path.join(backup_dir, self.__create_backup_filename())

        # Create the backup directory if it does not exist.
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # Delete older backups. - Commented out until full strategy determined.
        # self.__rolling_backup_deletion(backup_dir)
        
        logger.info("Taking backup ...")
        with tarfile.open(backup_name, "w:gz") as tar:
            logger.info(f"Backing up [{data_dir}] ...")
            tar.add(data_dir, arcname=os.path.basename(data_dir))

            logger.info(f"Backing up [{conf_dir}] ...")
            tar.add(conf_dir, arcname=os.path.basename(conf_dir))

        logger.info("Backup completed")

        return backup_name

    def __view_backups(self, ctx):
        """Display a list of available backups that were found in the backup folder

        """
        cli_context: appcli.CliContext = ctx.obj
        logger.info("Displaying all available backups.")

        backup_dir: Path = cli_context.backup_dir

        backup_dir_files = sorted(os.listdir(backup_dir), key=self.__parse_datetime_from_filename, reverse=True)
        for backup in backup_dir_files:
            print(backup)


    def __create_backup_filename(self):
        """Generate the filename of the backup .tgz file
           Format is "<APP_NAME>_<datetime.now>.tgz"

        Returns:
            The formatted .tgz filename
        """
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        return f"{self.cli_configuration.app_name.upper()}_{now.isoformat()}.tgz"

    def __rolling_backup_deletion(self, backup_dir):
        """Delete old backups, will only keep the last 7 backups organized by the date listed in the filename.

        Args:
            backup_dir (string): The directory that contains the backups.
        """
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
        
    def __parse_datetime_from_filename(self, filename):
        """Helper function to parse a datetime object from a filename.

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

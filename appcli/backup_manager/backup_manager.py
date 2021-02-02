#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles backing up and restoration of data.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

import os
import shutil
import tarfile
from datetime import datetime, timezone

# standard libraries
from pathlib import Path

# vendor libraries
import dateutil.parser

# local libraries
from appcli.backup_manager.remote_strategy import AwsS3Strategy
from appcli.logger import logger
from appcli.models.cli_context import CliContext


class BackupManager:
    """
    Utility class which contains methods for local backup/restoration of application configuration and data.
    """

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------
    def __init__(self, stack_variables):
        self.backup_variables = stack_variables.get("backup", {})

        self.number_of_backups_to_retain = self.backup_variables.get(
            "numberOfBackupsToKeep", 0
        )
        self.ignore_list = self.backup_variables.get("ignoreList", [])
        self.remote_strategy_config = self.backup_variables.get("remote", {})

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------
    def backup(self, ctx, number_of_backups_to_retain=-1):
        """Create a backup `.tgz` file that contains application data and configuration.
        Will shutdown the application and generate a backup containing CliContext.obj.data_dir and CliContext.obj.configuration_dir.
        Will also perform a rolling backup deletion if `number_of_backups_to_retain` is is either passed in or set in config.

        Args:
            ctx: Application context.
            number_of_backups_to_retain: int. The number of backups to retain locally, `-1` will use the value set in config. 0 will not delete any backups.

        Returns:
            backup_name (string): The filename of the generated backup that includes the full path.
        """
        cli_context: CliContext = ctx.obj
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
        backup_name: Path = os.path.join(
            backup_dir, self.__create_backup_filename(cli_context.app_name)
        )

        # Create the backup directory if it does not exist.
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # Delete older backups.
        number_of_backups_to_retain = (
            self.number_of_backups_to_retain
            if number_of_backups_to_retain == -1
            else number_of_backups_to_retain
        )
        if number_of_backups_to_retain > 0:
            self.__rolling_backup_deletion(cli_context.app_name, backup_dir)

        logger.info("Taking backup ...")
        with tarfile.open(backup_name, "w:gz") as tar:
            logger.info(f"Backing up [{data_dir}] ...")
            tar.add(
                data_dir,
                arcname=os.path.basename(data_dir),
                filter=self.__glob_tar_filter,
            )

            logger.info(f"Backing up [{conf_dir}] ...")
            tar.add(
                conf_dir,
                arcname=os.path.basename(conf_dir),
                filter=self.__glob_tar_filter,
            )

        logger.info("Backup completed")

        return backup_name

    def __glob_tar_filter(self, tarinfo):
        """
        Filter function for excluding files from the tgz if their full path matches any glob patterns set in the config.

        Args:
            tarinfo: TarInfo. A TarInfo object that represents the current file.
        Returns:
            The TarInfo object if we want to include it in the tgz, return None if we want to skip this file.
        """
        if any((Path(tarinfo.name).match(glob)) for glob in self.ignore_list):
            return None
        else:
            return tarinfo

    def restore(self, ctx, backup_filename):
        """Restore application data and configuration from the provided local backup `.tgz` file.
        This will create a backup of the existing data and config, remove the contents `conf`, `data` and `conf/.generated` and then extract the backup to the appropriate locations.
        `conf`, `data` and `conf/.generated` are mapped into appcli which means we keep the folder but replace their contents on restore.

        Args:
            backup_filename (string): The name of the file to use in restoring data. The path of the file will be pulled from `CliContext.obj.backup_dir`.
        """
        cli_context: CliContext = ctx.obj

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
        restore_backup_name = self.backup(
            ctx, 0
        )  # 0 ensures we don't accidentally delete our backup
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
                logger.error("Failed to delete %s. Reason: %s" % (file_path, e))

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
        Will allow extracted files to exclude the provided subfolder from their extracted path.

        Args:
            tf (tar): The tar file to extract.
            subfolder (string): The subfolder to exclude from the extraction path.
        """
        length_of_subfolder = len(subfolder)
        for member in tf.getmembers():
            if member.path.startswith(subfolder):
                member.path = member.path[length_of_subfolder:]
                yield member

    def view_backups(self, ctx):
        """Display a list of available backups that were found in the backup folder"""
        cli_context: CliContext = ctx.obj
        logger.info("Displaying all available backups.")

        backup_dir: Path = cli_context.backup_dir

        backup_dir_files = sorted(
            os.listdir(backup_dir),
            key=lambda x: self.__parse_datetime_from_filename(x, cli_context.app_name),
            reverse=True,
        )
        for backup in backup_dir_files:
            print(backup)

    def __create_backup_filename(self, app_name):
        """Generate the filename of the backup .tgz file
           Format is "<APP_NAME>_<datetime.now>.tgz"

        Args:
            app_name: str. The application name to be used in the naming of the tgz file.
        Returns:
            The formatted .tgz filename
        """
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        return f"{app_name.upper()}_{now.isoformat()}.tgz"

    def __rolling_backup_deletion(self, app_name, backup_dir):
        """Delete old backups, will only keep the last 7 backups organized by the date listed in the filename.

        Args:
            app_name: str. The application name to be used in the naming of the tgz file.
            backup_dir (string): The directory that contains the backups.
        """
        # Simply sort in Chronological descending order, and then delete from the appropriate index
        # onward.
        logger.info(
            f"Removing old backups - retaining at least the last [{self.number_of_backups_to_retain}] backups ..."
        )
        backup_dir_files = sorted(
            os.listdir(backup_dir),
            key=lambda x: self.__parse_datetime_from_filename(x, app_name),
            reverse=True,
        )
        backups_to_delete = backup_dir_files[
            self.number_of_backups_to_retain - 1:
        ]  # -1 as we're 0 indexed
        for backup_to_delete in backups_to_delete:
            backup_file: Path = Path(os.path.join(backup_dir, backup_to_delete))
            logger.info(f"Deleting backup file [{backup_file}]")
            os.remove(backup_file)

    def __parse_datetime_from_filename(self, filename, app_name):
        """Helper function to parse a datetime object from a filename.

        Args:
            filename (string): The filename to parse.
            app_name: str. The application name to be used in the naming of the tgz file.

        Returns:
            The datetime object.
        """

        # Filename is <app_name>_<date>.tgz, need to strip the app_name and file extension.
        timestamp = Path(filename).stem.replace(app_name.upper() + "_", "")

        # Filename may not be in the expected format, in that case assign it a sort value of now
        # so it appears at the top of the list.
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        sort_key = now.isoformat()

        try:
            return dateutil.parser.parse(timestamp)
        except ValueError:
            logger.info(f"Unexpected backup found {filename}")

        return dateutil.parser.parse(sort_key)


class RemoteStrategyFactory:
    """
    Factory for getting all remote strategies that match the config
    """

    @staticmethod
    def get_strategy(backup_manager, key_file: Path):
        strategies = {"S3": AwsS3Strategy}

        backup_strategies = []

        for backup in backup_manager.remote_strategy_config:
            cl = strategies.get(backup["type"], lambda: "Invalid remote strategy")

            if isinstance(cl, str):
                logger.error(
                    f"No remote backup strategies found for type {backup['type']}"
                )

            strategy = cl(backup, key_file)

            if RemoteStrategyFactory.__frequency_check(strategy.frequency):
                backup_strategies.append(strategy)

        return backup_strategies

    def __frequency_check(frequency):
        """
        Check if today matches the pseudo cron `frequency`.
        Frequency format is `* * *`:
        First `*` is the day of the month.
        Second `*` is the month.
        Third `*` is the day of the week starting with monday=0.
        `*` is a wildcard that is always matched.
        e.g.
        `* * *` Will always return True.
        `* * 0` Will only return True on Mondays.

        Args:
            frequency: str. A frequency string that is checked to see if a backup should occur today.
        Returns:
            True if today matches the frequency, False if it does not.
        """
        if not len(frequency) == 5:
            logger.error(f"Frequency string is invalid - {frequency}")
            return False

        toReturn = True

        day_of_month = frequency[0]
        month = frequency[2]
        day_of_week = frequency[4]

        today = datetime.today()

        if day_of_month.isnumeric():
            if not int(day_of_month) == today.day:
                toReturn = False

        if month.isnumeric():
            if not int(month) == today.month:
                toReturn = False

        if day_of_week.isnumeric():
            if not int(day_of_week) == today.weekday():
                toReturn = False

        return toReturn

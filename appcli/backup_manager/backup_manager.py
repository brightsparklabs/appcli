#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles backing up and restoration of data of the configuration and data directories.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""


# standard libraries
import os
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tarfile import TarInfo
from typing import List, Optional

# vendor libraries
from dataclasses_json import dataclass_json

# local libraries
from appcli.backup_manager.remote_strategy import RemoteBackup
from appcli.backup_manager.remote_strategy_factory import RemoteStrategyFactory
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext


@dataclass_json
@dataclass
class BackupManager:
    """
    Utility class which contains methods for local backup/restoration of application configuration and data.
    """

    backup_limit: Optional[int] = 0
    ignore_list: Optional[List[str]] = field(default_factory=list)
    remote: Optional[List[RemoteBackup]] = field(default_factory=list)

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------

    def get_remote_strategies(self):
        """
        Get a list of remote strategy objects that represent valid remote strategies that should be ran today.

        Returns:
            A list of remote strategy objects.
        """

        backup_strategies = []

        for backup in self.remote:

            try:
                strategy = RemoteBackup.from_dict(backup)

                strategy.strategy = RemoteStrategyFactory.get_strategy(
                    strategy.strategy_type, strategy.configuration
                )
                strategy.strategy.name = strategy.name

                if strategy.should_run():
                    backup_strategies.append(strategy)

            except TypeError as e:
                logger.error(e)

        return backup_strategies

    def backup(self, ctx, allow_rolling_deletion: bool = True) -> Path:
        """Create a backup `.tgz` file that contains application data and configuration.
        Will shutdown the application and generate a backup containing CliContext.obj.data_dir and CliContext.obj.configuration_dir.
        Will also perform a rolling backup deletion if `allow_rolling_deletion` is True.

        Args:
            ctx: Application context.
            allow_rolling_deletion: bool. Enable rolling backups, set to False to disable rolling backups and keep all backup files.

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
            # the SystemExit.
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

        logger.info("Taking backup ...")

        tar_filter = (
            self.__glob_tar_filter
            if (isinstance(self.ignore_list, list) and self.ignore_list)
            else (lambda tarinfo: tarinfo)
        )

        with tarfile.open(backup_name, "w:gz") as tar:
            logger.info(f"Backing up [{data_dir}] ...")
            tar.add(
                data_dir,
                arcname=os.path.basename(data_dir),
                filter=tar_filter,
            )

            logger.info(f"Backing up [{conf_dir}] ...")
            tar.add(
                conf_dir,
                arcname=os.path.basename(conf_dir),
                filter=tar_filter,
            )

        # Delete older backups.
        if allow_rolling_deletion:
            self.__rolling_backup_deletion(cli_context.app_name, backup_dir)

        logger.info("Backup completed. The application has been shut down.")

        return backup_name

    def __glob_tar_filter(self, tarinfo: TarInfo):
        """
        Filter function for excluding files from the tgz if their full path matches any glob patterns set in the config.

        Args:
            tarinfo: TarInfo. A TarInfo object that represents the current file.
        Returns:
            The TarInfo object if we want to include it in the tgz, return None if we want to skip this file.
        """
        # If our glob list is not set or empty then we don't want to ignore any files.
        if not isinstance(self.ignore_list, list) or not self.ignore_list:
            return tarinfo

        if any((Path(tarinfo.name).match(glob)) for glob in self.ignore_list):
            return None
        else:
            return tarinfo

    def restore(self, ctx, backup_filename: Path):
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
        backup_name: Path = Path(os.path.join(backup_dir, backup_filename))

        logger.info("Initiating system restore")

        # Check that the backup file exists.
        if not backup_name.is_file():
            error_and_exit(f"Backup file {backup_name} not found.")
            return

        # Stop the system.
        logger.info("Stopping system ...")
        services_cli = cli_context.commands["service"]
        try:
            ctx.invoke(services_cli.commands["shutdown"])
        except SystemExit:
            # At completion, the invoked command tries to exit the script, so we have to catch
            # the SystemExit.
            pass

        # Perform a backup of the existing application config and data.
        logger.info("Creating backup of existing application data and configuration")
        restore_backup_name = self.backup(
            ctx, allow_rolling_deletion=False
        )  # 0 ensures we don't accidentally delete our backup
        logger.info(f"Backup generated before restore was: {restore_backup_name}")

        # Extract conf and data directories from the tar.
        # This will overwrite the contents of each directory, anything not in the backup (such as files matching the glob pattern) will be left alone.
        try:
            with tarfile.open(backup_name) as tar:
                tar.extractall(conf_dir, members=self.__members(tar, "conf/"))
                tar.extractall(data_dir, members=self.__members(tar, "data/"))

        except Exception as e:
            logger.error(f"Failed to extract backup. Reason: {e}")

        logger.info("Restore complete. The application has been shut down.")

    def __members(self, tf, subfolder: str):
        """Helper function for extracting folders from a tar ball.
        Will allow extracted files to exclude the provided subfolder from their extracted path.

        Args:
            tf (tar): The tar file to extract.
            subfolder (string): The subfolder to exclude from the extraction path.
        """
        length_of_subfolder = len(subfolder)
        for member in tf.getmembers():
            # For each file (member) in the tar file check to see if it starts with the specified string.
            if member.path.startswith(subfolder):
                # If it does start with that string, exclude that string from the start of the Path we are extracting it to.
                # This allows us to put the extracted files straight into their respective `conf` or `data` directories.
                member.path = member.path[length_of_subfolder:]
                yield member

    def view_backups(self, ctx):
        """Display a list of available backups that were found in the backup folder."""
        cli_context: CliContext = ctx.obj
        logger.info("Displaying all available backups.")

        backup_dir: Path = cli_context.backup_dir

        backup_dir_files = sorted(
            os.listdir(backup_dir),
            reverse=True,
        )
        for backup in backup_dir_files:
            print(backup)

    def __create_backup_filename(self, app_name: str):
        """Generate the filename of the backup .tgz file.
           Format is "<APP_NAME>_<datetime.now>.tgz".

        Args:
            app_name: str. The application name to be used in the naming of the tgz file.
        Returns:
            The formatted .tgz filename.
        """
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        return f"{app_name.upper()}_{now.isoformat()}.tgz"

    def __rolling_backup_deletion(self, app_name: str, backup_dir: Path):
        """Delete old backups, will only keep the most recent backups.
        The number of backups to keep is specified in the stack settings configuration file.
        Any files in the backup directory that do not match the filename pattern will be excluded
        from deletion and will not count towards the number of backups to keep.

        Args:
            app_name: str. The application name to be used in the naming of the tgz file.
            backup_dir (string): The directory that contains the backups.
        """

        if self.backup_limit == 0:
            return

        # Sort in Chronological descending order, and then delete from the appropriate index
        # onward.
        logger.info(
            f"Removing old backups - retaining at least the last [{self.backup_limit}] backups ..."
        )

        # 'Get all files from our backup directory
        backup_files = os.listdir(backup_dir)

        # Sort the backups by the DateTime specified in the filename.
        backup_dir_files = sorted(
            backup_files,
            reverse=True,
        )
        # Get the backups to delete by taking our sorted list of backups and creating a sub-list starting
        # from the index matching the number of backups to retain to the end of the list
        backups_to_delete = backup_dir_files[
            self.backup_limit :  # noqa: E203 - Disable flake8 error on spaces before a `:`
        ]  # -1 as we're 0 indexed
        for backup_to_delete in backups_to_delete:
            backup_file: Path = Path(os.path.join(backup_dir, backup_to_delete))
            logger.info(f"Deleting backup file [{backup_file}]")
            os.remove(backup_file)
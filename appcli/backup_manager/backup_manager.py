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
from dataclasses import MISSING, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from tarfile import TarFile, TarInfo
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

    backup_limit: Optional[int] = field(default=0)
    """ The number of backups to retain locally. Set to 0 to never delete a backup. """
    ignore_list: Optional[List[str]] = field(default_factory=list)
    """ An optional list of glob patterns. If any of these patterns match the full path of a file to be backed up then that file will be ignored. """
    remote: Optional[List[RemoteBackup]] = field(default_factory=list)
    """ An optional list of remote backup strategies of potentially varing types. """

    def __post_init__(self):
        """Called after __init__().
        None of the fields should be allowed to be 'None' - if any are, override with the default.
        """

        for f in fields(self):
            val = getattr(self, f.name)
            if val is None:
                # If the field is 'empty' and set to None in the settings, default to:
                # - f.default if it's defined, otherwise
                # - f.default_factory() if f.default_factory is defined, otherwise
                # - None (as there's no other reasonable default).
                default_value = None
                if f.default != MISSING:
                    default_value = f.default
                elif f.default_factory != MISSING:
                    default_value = f.default_factory()

                logger.debug(
                    f"Overriding 'None' for [{f.name}] with default [{default_value}]"
                )
                setattr(self, f.name, default_value)

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
                remote_backup = RemoteBackup.from_dict(backup)

                remote_backup.strategy = RemoteStrategyFactory.get_strategy(
                    remote_backup.strategy_type, remote_backup.configuration
                )
                remote_backup.strategy.name = remote_backup.name

                if remote_backup.should_run():
                    backup_strategies.append(remote_backup)

            except TypeError as e:
                logger.error(f"Failed to create remote strategy - {e}")

        return backup_strategies

    def backup(self, ctx, allow_rolling_deletion: bool = True) -> Path:
        """Create a backup `.tgz` file that contains application data and configuration.
        Will shutdown the application and generate a backup containing CliContext.obj.data_dir and
        CliContext.obj.configuration_dir. Will also perform a rolling backup deletion if `allow_rolling_deletion` is
        True.

        Args:
            allow_rolling_deletion: (bool). Enable rolling backups (default True). Set to False to disable rolling
                backups and keep all backup files.

        Returns:
            backup_name (Path): The filename of the generated backup that includes the full path.
        """
        cli_context: CliContext = ctx.obj
        logger.info("Initiating system backup")

        logger.info("Stopping application services ...")
        services_cli = cli_context.commands["service"]
        try:
            ctx.invoke(services_cli.commands["shutdown"])
        except SystemExit:
            # At completion, the invoked command tries to exit the script, so we have to catch
            # the SystemExit.
            pass

        backup_dir: Path = cli_context.backup_dir

        # Create the backup directory if it does not exist.
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Taking backup ...")

        backup_name: Path = os.path.join(
            backup_dir, self.__create_backup_filename(cli_context.app_name)
        )
        with tarfile.open(backup_name, "w:gz") as tar:
            data_dir: Path = cli_context.data_dir
            logger.info(f"Backing up [{data_dir}] ...")
            tar.add(
                data_dir,
                arcname=os.path.basename(data_dir),
                filter=self.__glob_tar_filter,
            )

            conf_dir: Path = cli_context.configuration_dir
            logger.info(f"Backing up [{conf_dir}] ...")
            tar.add(
                conf_dir,
                arcname=os.path.basename(conf_dir),
                filter=self.__glob_tar_filter,
            )

        # Delete older backups.
        if allow_rolling_deletion:
            self.__rolling_backup_deletion(cli_context.app_name, backup_dir)

        logger.info("Backup completed. Application services have been shut down.")

        return backup_name

    def __glob_tar_filter(self, tarinfo: TarInfo):
        """
        Filter function for excluding files from the tgz if their full path matches any glob patterns set in the config.

        Args:
            tarinfo: (TarInfo). A TarInfo object that represents the current file.
        Returns:
            The TarInfo object if we want to include it in the tgz, None if we want to skip this file.
        """

        if any((Path(tarinfo.name).match(glob)) for glob in self.ignore_list):
            return None
        else:
            return tarinfo

    def restore(self, ctx, backup_filename: Path):
        """Restore application data and configuration from the provided local backup `.tgz` file.
        This will create a backup of the existing data and config, remove the contents `conf`, `data` and
        `conf/.generated` and then extract the backup to the appropriate locations.
        `conf`, `data` and `conf/.generated` are mapped into appcli which means we keep the folder but replace their
        contents on restore.

        Args:
            backup_filename (string): The name of the file to use in restoring data. The path of the file will be pulled from `CliContext.obj.backup_dir`.
        """
        cli_context: CliContext = ctx.obj

        logger.info("Initiating system restore")

        # Check that the backup file exists.
        backup_dir: Path = cli_context.backup_dir
        backup_name: Path = Path(os.path.join(backup_dir, backup_filename))
        if not backup_name.is_file():
            error_and_exit(f"Backup file [{backup_name}] not found.")
            return

        # Stop the system.
        logger.info("Stopping application services ...")
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
        )  # False ensures we don't accidentally delete our backup
        logger.info(f"Backup generated before restore was: [{restore_backup_name}]")

        # Extract conf and data directories from the tar.
        # This will overwrite the contents of each directory, anything not in the backup (such as files matching the glob pattern) will be left alone.
        try:
            with tarfile.open(backup_name) as tar:
                conf_dir: Path = cli_context.configuration_dir
                tar.extractall(conf_dir, members=self.__members(tar, "conf/"))
                data_dir: Path = cli_context.data_dir
                tar.extractall(data_dir, members=self.__members(tar, "data/"))

        except Exception as e:
            logger.error(f"Failed to extract backup. Reason: {e}")

        logger.info("Restore completed. Application services have been shut down.")

    def __members(self, tf: TarFile, subfolder: str):
        """Helper function for extracting folders from a tar ball.
        Will allow extracted files to exclude the provided subfolder from their extracted path.

        Args:
            tf (TarFile): The tar file to extract.
            subfolder (string): The subfolder to exclude from the extraction path.
        """
        length_of_subfolder = len(subfolder)
        for member in tf.getmembers():
            # For each file (member) in the tar file check to see if it starts with the specified string (subfolder).
            if member.path.startswith(subfolder):
                # If it does start with that string, exclude that string from the start of the Path we are extracting it to.
                # This allows us to put the extracted files straight into their respective `conf` or `data` directories.
                member.path = member.path[length_of_subfolder:]
                yield member

    def view_backups(self, ctx):
        """Display a list of available backups that were found in the backup folder."""
        cli_context: CliContext = ctx.obj
        logger.info("Displaying all locally-available backups.")

        backup_dir: Path = cli_context.backup_dir

        backup_dir_files = sorted(
            os.listdir(backup_dir),
            reverse=True,
        )
        for backup in backup_dir_files:
            print(backup)

    def __create_backup_filename(self, app_name: str) -> str:
        """Generate the filename of the backup .tgz file.
           Format is "<APP_NAME>_<datetime.now>.tgz".

        Args:
            app_name: (str). The application name to be used in the naming of the tgz file.
        Returns:
            The formatted .tgz filename.
        """
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        return f"{app_name.upper()}_{now.isoformat()}.tgz"

    def __rolling_backup_deletion(self, backup_dir: Path):
        """Delete old backups, will only keep the most recent backups.
        The number of backups to keep is specified in the stack settings configuration file.
        Note that the age of the backup is derived from the alphanumerical order of the backup filename.
        This means that any supplementary files in the backup directory could have unintended consequences during
        rolling deletion.
        Backup files are intentionally named with a datetime stamp to enable age ordering.

        Args:
            backup_dir (Path): The directory that contains the backups.
        """

        # If the backup limit is set to 0 then we never want to delete a backup.
        if self.backup_limit == 0:
            return

        logger.info(
            f"Removing old backups - retaining at least the last [{self.backup_limit}] backups ..."
        )

        # Get all files from our backup directory
        backup_files = os.listdir(backup_dir)

        # Sort the backups alphanumerically by filename. Note that this assumes all files in the backup dir are backup
        # files that use a time-sortable naming convention.
        backup_dir_files = sorted(
            backup_files,
            reverse=True,
        )
        # Get the backups to delete by taking our sorted list of backups and then delete from the appropriate index
        # onward.
        backups_to_delete = backup_dir_files[
            self.backup_limit :  # noqa: E203 - Disable flake8 error on spaces before a `:`
        ]
        for backup_to_delete in backups_to_delete:
            backup_file: Path = Path(os.path.join(backup_dir, backup_to_delete))
            logger.info(f"Deleting backup file [{backup_file}]")
            os.remove(backup_file)

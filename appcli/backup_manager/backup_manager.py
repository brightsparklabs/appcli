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
import glob
import copy

# vendor libraries
from dataclasses_json import dataclass_json

# local libraries
from appcli.backup_manager.remote_strategy import RemoteBackup
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext

@dataclass_json
@dataclass
class GlobList:
    data_globs: Optional[List[str]] = field(default_factory=list)
    """ The glob pattern to match. `**/*` to match everything """

    conf_globs: Optional[List[str]] = field(default_factory=list)
    """  """



@dataclass_json
@dataclass
class BackupConfig:
    """
    Utility class which contains methods for local backup/restoration of application configuration and data.
    """
    name: str
    """ The name of the folder to place the local backup in. """

    backup_limit: Optional[int] = field(default=0)
    """ The number of backups to retain locally. Set to 0 to never delete a backup. """

    exclude_list: Optional[GlobList] = field(default_factory=GlobList)
    """ An optional list of glob patterns. If any of these patterns match the full path of a file to be backed up then that file will be ignored. """

    include_list: Optional[GlobList] = field(default_factory=GlobList)
    """ An optional list of glob patterns. If provided only files that match the pattern will be backed up. """

    remote_backups: Optional[List[RemoteBackup]] = field(default_factory=list)
    """ An optional list of remote backup strategies of potentially varing types. """

    def __post_init__(self):
        """Called after __init__().
        None of the fields should be allowed to be 'None' - if any are, override with the default.
        """
        if self.include_list is None:
            self.include_list = GlobList(["**/*"], ["**/*"])

        if not self.include_list.conf_globs:
            self.include_list.conf_globs = ["**/*"]
        if not self.include_list.data_globs:
            self.include_list.data_globs = ["**/*"]


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


        # 
        backup_dir: Path = cli_context.backup_dir
        
        # 
        sub_backup_dir: Path = Path(os.path.join(backup_dir, self.name))

        # Create the backup directory if it does not exist.
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # Create the subfolder for the backup name if it does not exist.
        if not sub_backup_dir.exists():
            sub_backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Taking backup [{self.name}]")


        # 
        backup_name: Path = os.path.join(
            sub_backup_dir, self.__create_backup_filename(cli_context.app_name)
        )

        
        data_dir: Path = cli_context.data_dir
        conf_dir: Path = cli_context.configuration_dir


        config_file_list: set(Path) = self.__determine_file_list_from_glob(conf_dir, self.include_list.conf_globs, self.exclude_list.conf_globs)
        data_file_list: set(Path) = self.__determine_file_list_from_glob(data_dir, self.include_list.data_globs, self.exclude_list.data_globs)
     
        with tarfile.open(backup_name, "w:gz") as tar:

            logger.info(f"Backing up [{conf_dir}] ...")

            if config_file_list:
                for f in config_file_list:
                    tar.add(f, arcname= os.path.join(os.path.basename(conf_dir), os.path.relpath(f, conf_dir)))

            if data_file_list:
                for f in data_file_list:
                    tar.add(f, arcname= os.path.join(os.path.basename(data_dir), os.path.relpath(f, data_dir)))
                
        # Delete older backups.
        if allow_rolling_deletion:
            self.__rolling_backup_deletion(sub_backup_dir)

        logger.info("Backup completed. Application services have been shut down.")

        return backup_name

    def __determine_file_list_from_glob(self, path_to_backup: Path, include_globs, exclude_globs):
        
        included_globbed_files: set(Path) = set()
        for glob in include_globs: 
            files = path_to_backup.glob(glob)
            
            for item in files:
                if not item.is_dir():
                    included_globbed_files.add(item)

        excluded_globbed_files: set(Path) = set()
        for glob in exclude_globs: 
            files = path_to_backup.glob(glob)
            for item in files:
                if not item.is_dir():
                    excluded_globbed_files.add(item)

        files_to_backup: set(Path) = included_globbed_files - excluded_globbed_files

        return files_to_backup


    def get_remote_backups(self) -> List[RemoteBackup]:
        """Get a list of remote strategy objects that represent valid remote strategies that should be ran today.

        Returns:
            List[RemoteBackup]: A list of configured remote backups.
        """

        backup_strategies: List[RemoteBackup] = []

        for remote_configuration in self.remote_backups:

            try:
                remote_backup: RemoteBackup = RemoteBackup.from_dict(
                    remote_configuration
                )

                if remote_backup.should_run():
                    backup_strategies.append(remote_backup)

            except TypeError as e:
                logger.error(f"Failed to create remote strategy - {e}")

        return backup_strategies

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


    

@dataclass_json
@dataclass
class BackupManager:
    backups: BackupConfig

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------


    def mainBackup(self, ctx):
        cli_context: CliContext = ctx.obj

        # Get the key file for decrypting encrypted values used in a remote backup.
        key_file = cli_context.get_key_file()

        for backup in self.backups:

            b = BackupConfig.from_dict(backup)

            # create the backup
            b.backup(ctx)

            # Get any remote backup strategies.
            remote_backups = b.get_remote_backups()

            # Execute each of the remote backup strategies with the local backup file.
            for remote_backup in remote_backups:
                try:
                    #remote_backup.backup(backup_filename, key_file)
                    logger.info(remote_backup)
                    pass
                except Exception as e:
                    logger.error(
                        f"Error while executing remote strategy [{remote_backup.name}] - {e}"
                    )
                    traceback.print_exc()

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
                tar.extractall(conf_dir, members=self.__members(tar, os.path.basename(conf_dir)))
                data_dir: Path = cli_context.data_dir
                tar.extractall(data_dir, members=self.__members(tar, os.path.basename(data_dir)))

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

        files = [os.path.join(path[len(str(backup_dir)):].lstrip("/"), name) for path, subdirs, files in os.walk(backup_dir) for name in files]


        backup_dir_files = sorted(
            files,
            reverse=True,
        )
        for backup in backup_dir_files:
            print(backup)

    
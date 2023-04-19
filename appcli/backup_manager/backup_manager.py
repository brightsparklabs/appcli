#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles backing up and restoration of data of the configuration and data directories.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import datetime
import os
import tarfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from tarfile import TarFile
from typing import List, Optional, Set

# vendor libraries
import cronex
from click import Context
from dataclasses_json import dataclass_json
from slugify import slugify

# local libraries
from appcli.backup_manager.remote_strategy import RemoteBackup
from appcli.common.data_class_extensions import DataClassExtensions
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext


@dataclass_json
@dataclass
class GlobList(DataClassExtensions):
    """The container class for lists of globs for the include and exclude lists."""

    include_list: Optional[List[str]] = field(default_factory=lambda: ["**/*"])
    """ A List of glob patterns that represents the files to be added to the backup. Will default to everything. """

    exclude_list: Optional[List[str]] = field(default_factory=lambda: ["[]"])
    """ A List of glob patterns that represents the files to be excluded from the backup. Will default to nothing. """


@dataclass_json
@dataclass
class FileFilter(DataClassExtensions):
    """The container class for the data and conf directory include/exclude lists."""

    data_dir: Optional[GlobList] = field(default_factory=lambda: GlobList())
    """ The GlobList for the data directory. """
    conf_dir: Optional[GlobList] = field(default_factory=lambda: GlobList())
    """ The GlobList for the conf directory. """


@dataclass_json
@dataclass
class BackupConfig(DataClassExtensions):
    """
    Backup configuration class which contains methods for local backup of application configuration and data.
    """

    name: str
    """ The name of the folder to place the local backup in. """

    backup_limit: Optional[int] = field(default_factory=lambda: 0)
    """ The number of backups to retain locally. Set to 0 to never delete a backup. """

    file_filter: Optional[FileFilter] = field(
        default_factory=lambda: FileFilter(GlobList(), GlobList())
    )
    """
    A FileFilter which represents the files to include or exclude from the backup for the conf and data directories.
    If not set will default to include everything and exclude nothing.
    """

    remote_backups: Optional[List[RemoteBackup]] = field(default_factory=list)
    """ An optional list of remote backup strategies of potentially varing types. """

    frequency: Optional[str] = field(default_factory=lambda: "* * *")
    """ An optional CRON frequency with the time stripped out i.e. `* * *` for specifying when this strategy should run. """

    def get_filesystem_safe_name(self) -> str:
        """
        Get the backup name as a filessystem-safe name.
        """
        return slugify(self.name)

    def should_run(self) -> bool:
        """
        Verify if the backup should run based on todays date and the frequency value set.

        Returns:
            True if the frequency matches today, False if it does not.
        """

        # Our configuration is just the last 3 values of a cron pattern, prepend hour/minute as wild-cards.
        cron_frequency = f"* * {self.frequency}"

        try:
            job = cronex.CronExpression(cron_frequency)
        except ValueError as e:
            logger.error(
                f"Frequency for remote strategy [{self.name}] is not valid [{self.frequency}]. [{e}]"
            )
            return False
        if not job.check_trigger(time.gmtime(time.time())[:5]):
            logger.debug(
                f"Backup strategy [{self.name}] will not run due to frequency [{self.frequency}] not matching today."
            )
            return False

        return True

    def backup(self, ctx, allow_rolling_deletion: bool = True) -> Path:
        """Create a backup `.tgz` file that contains application data and configuration.
        Will perform a rolling backup deletion if `allow_rolling_deletion` is `True`.

        Args:
            allow_rolling_deletion: (bool). Enable rolling backups (default True). Set to False to disable rolling
                backups and keep all backup files.

        Returns:
            Path: The filename of the generated backup that includes the full path.
        """
        cli_context: CliContext = ctx.obj

        backup_dir: Path = cli_context.backup_dir

        # Get the path to place the backup in by combining the backup_dir and the name of the backup.
        sub_backup_dir: Path = Path(
            os.path.join(backup_dir, self.get_filesystem_safe_name())
        )

        # Create the backup directory if it does not exist.
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # Create the subfolder for the backup name if it does not exist.
        if not sub_backup_dir.exists():
            sub_backup_dir.mkdir(parents=True, exist_ok=True)

        # Get the backup name to use when creating the tar.
        backup_name: Path = os.path.join(
            sub_backup_dir,
            self.__create_backup_filename(
                cli_context.app_name_slug, self.get_filesystem_safe_name()
            ),
        )

        data_dir: Path = cli_context.data_dir
        conf_dir: Path = cli_context.configuration_dir

        # Determine the list of conf files to add to the tar.
        config_file_list: set(Path) = self.__determine_file_list_from_glob(
            conf_dir, self.file_filter.conf_dir
        )
        logger.debug(f"Config files to backup: [{config_file_list}]")
        # Determine the list of data files to add to the tar.
        data_file_list: set(Path) = self.__determine_file_list_from_glob(
            data_dir, self.file_filter.data_dir
        )
        logger.debug(f"Data files to backup: [{data_file_list}]")

        # Backup the file lists to a tar file.
        with tarfile.open(backup_name, "w:gz") as tar:
            logger.debug(f"Backing up [{conf_dir}] ...")

            if config_file_list:
                for f in config_file_list:
                    tar.add(
                        f,
                        arcname=os.path.join(
                            os.path.basename(conf_dir), os.path.relpath(f, conf_dir)
                        ),
                    )

            logger.debug(f"Backing up [{data_dir}] ...")
            if data_file_list:
                for f in data_file_list:
                    tar.add(
                        f,
                        arcname=os.path.join(
                            os.path.basename(data_dir), os.path.relpath(f, data_dir)
                        ),
                    )

        logger.info(f"Backup created at [{backup_name}]")

        # Delete older backups.
        if allow_rolling_deletion:
            self.__rolling_backup_deletion(sub_backup_dir)

        return backup_name

    def __determine_file_list_from_glob(
        self, path_to_backup: Path, globs: GlobList
    ) -> Set[Path]:
        """
        Determine the list of files to backup in the path provided based on the include/exclude lists in the provided GlobList

        Args:
            path_to_backup: (Path). The path to use when generating the list of files.
            globs: (GlobList). A GlobList which contains the include/exclude list used to filter the files found in the path.

        Returns:
            set(Path): A set of files that need to be backed up.
        """

        # Get a set of files that should be included in the backup.
        included_globbed_files: set(Path) = self.__get_files_from_globs(
            path_to_backup, globs.include_list
        )
        logger.debug(
            f"Included files, glob: [{globs.include_list}], path: [{path_to_backup}], included files: [{included_globbed_files}]"
        )
        # Get a set of files that should be excluded from the backup.
        excluded_globbed_files: set(Path) = self.__get_files_from_globs(
            path_to_backup, globs.exclude_list
        )
        logger.debug(
            f"Excluded files, glob: [{globs.exclude_list}], path: [{path_to_backup}], excluded files: [{excluded_globbed_files}]"
        )

        # Determine the files that need to be backed up by removing the exclude set from the include set.
        filtered_files: set(Path) = included_globbed_files - excluded_globbed_files
        logger.debug(f"Final set of files to include: [{filtered_files}]")

        return filtered_files

    def __get_files_from_globs(self, path_to_backup: Path, globs: List[str]):
        """
        Get a list of files in the provided path that match the glob patterns provided.

        Args:
            path_to_backup: (Path). The path to use when generating the list of files.
            globs: (List[str]). A list of glob patterns which we want to use to find files in the provided path.

        Returns:
            set(Path): A set of files that match the provided glob patterns.
        """
        all_files: set(Path) = set()
        for glob in globs:
            files = path_to_backup.glob(glob)
            for item in files:
                # Glob pattern matching returns everything that matches the pattern including directories and all files (and the directory it is being run in).
                # Including directories is troublesome as if we pass a directory to the python tar function it will add that directories
                # tree recursively where as glob logic indicates that it should only add the folder with no contents.
                # If we match glob logic exactly and force an empty folder into the tar then it serves no purpose as it is not data or config and becomes convoluted.
                # To resolve this we do not add folders to the list of files to backup.
                # This also solves the problem where a glob pattern can match the directory it is ran in and stops duplicated files from being added to the tar as each file can only exist once in the set.
                if not item.is_dir():
                    all_files.add(item)

        return all_files

    def get_remote_backups(self) -> List[RemoteBackup]:
        """Get the list of remote strategy objects for this backup configuration.

        Returns:
            List[RemoteBackup]: A list of configured remote backups.
        """

        backup_strategies: List[RemoteBackup] = []

        for remote_configuration in self.remote_backups:
            try:
                remote_backup: RemoteBackup = RemoteBackup.from_dict(
                    remote_configuration
                )

                backup_strategies.append(remote_backup)

            except TypeError as e:
                logger.error(f"Failed to create remote strategy - {e}")

        return backup_strategies

    def __create_backup_filename(self, app_name_slug: str, backup_name: str) -> str:
        """Generate the filename of the backup .tgz file.
            Format is "<APP_NAME_SLUG>_<BACKUP_NAME>_<datetime.now>.tgz".

        Args:
            app_name_slug: (str). The application name to be used in the naming of the tgz file.
            backup_name: (str). The name of the backup being taken.
        Returns:
            The formatted .tgz filename.
        """
        # datetime's ISO format includes the ':' separator for the `hours:minutes:seconds`.
        # Since we're using this format in the filename of the backup, the backup filename
        # will include the ':' character.
        # Tools like `tar` (by default) expects files with ':' in the name to be a remote
        # resouces. To avoid this issue, we remove all ':'.
        now: str = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace(":", "")
        )
        return f"{app_name_slug.upper()}_{backup_name.upper()}_{now}.tgz"

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
            logger.debug("Backup limit is 0 - skipping rolling deletion.")
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
    """
    Backup manager class that contains all backup definitions.
    """

    backups: BackupConfig

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------

    def backup(
        self, ctx: Context, backup_name: str = None, allow_rolling_deletion: bool = True
    ) -> List[Path]:
        """
        Perform all backups present in the configuration file.

        Args:
            ctx: (Context). The current Click Context.
            allow_rolling_deletion: (bool). Enable rolling backups (default True). Set to False to disable rolling
                backups and keep all backup files.

        Returns:
            List[Path]: The list of backup files generated by running all backups.
        """

        cli_context: CliContext = ctx.obj
        logger.info("Initiating system backup")

        # Get the key file for decrypting encrypted values used in a remote backup.
        key_file = cli_context.get_key_file()

        completed_backups = []

        for backup_config in self.backups:
            backup = BackupConfig.from_dict(backup_config)

            if backup_name is not None and backup.name != backup_name:
                logger.debug(
                    f"Skipping backup [{backup.name}] - only running backup [{backup_name}]"
                )
                continue

            # Check if the set frequency matches today, if it does not then do not continue with the current backup.
            if not backup.should_run():
                continue

            # create the backup
            logger.debug(f"Backup [{backup.name}] running...")
            backup_filename = backup.backup(ctx, allow_rolling_deletion)
            completed_backups.append((backup.name, backup_filename))
            logger.debug(
                f"Backup [{backup.name}] complete. Output file: [{backup_filename}]"
            )

            # Get any remote backup strategies.
            remote_backups = backup.get_remote_backups()

            # Execute each of the remote backup strategies with the local backup file.
            for remote_backup in remote_backups:
                try:
                    logger.debug(
                        f"Backup [{backup.name}] remote backup [{remote_backup.name}] running..."
                    )
                    remote_backup.backup(backup_filename, key_file)
                    logger.debug(
                        f"Backup [{backup.name}] remote backup [{remote_backup.name}] complete."
                    )
                except Exception as e:
                    logger.error(
                        f"Error while executing remote strategy [{remote_backup.name}] - {e}"
                    )
                    traceback.print_exc()

        logger.info("Backups complete.")
        if len(completed_backups) > 0:
            logger.debug(f"Completed backups [{completed_backups}].")
        else:
            logger.warning(
                "No backups successfully ran or completed. Use --debug flag for more detailed logs."
            )
        return completed_backups

    def backup_file_exists(self, ctx, backup_filename: Path) -> bool:
        """
        Checks if a backup file exists. Returns True if it does, otherwise False.
        """
        cli_context: CliContext = ctx.obj
        backup_dir: Path = cli_context.backup_dir
        backup_name: Path = Path(os.path.join(backup_dir, backup_filename))
        return backup_name.is_file()

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

        logger.info(f"Initiating system restore with backup [{backup_filename}]")

        # Check that the backup file exists.
        backup_dir: Path = cli_context.backup_dir
        backup_name: Path = Path(os.path.join(backup_dir, backup_filename))
        if not backup_name.is_file():
            error_and_exit(f"Backup file [{backup_name}] not found.")

        # Perform a backup of the existing application config and data.
        logger.debug("Backup existing application data and configuration")
        restore_backup_name = self.backup(
            ctx, allow_rolling_deletion=False
        )  # False ensures we don't accidentally delete our backup
        logger.debug(f"Backup(s) complete. Generated backups: [{restore_backup_name}]")

        # Extract conf and data directories from the tar.
        # This will overwrite the contents of each directory, anything not in the backup (such as files matching the exclude glob patterns) will be left alone.
        try:
            with tarfile.open(backup_name) as tar:
                conf_dir: Path = cli_context.configuration_dir
                data_dir: Path = cli_context.data_dir

                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)

                    prefix = os.path.commonprefix([abs_directory, abs_target])

                    return prefix == abs_directory

                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")

                    tar.extractall(path, members, numeric_owner=numeric_owner)

                safe_extract(
                    tar=tar,
                    path=conf_dir,
                    members=self.__members(tar, os.path.basename(conf_dir)),
                )

                safe_extract(
                    tar=tar,
                    path=data_dir,
                    members=self.__members(tar, os.path.basename(data_dir)),
                )

        except Exception as e:
            logger.error(f"Failed to extract backup. Reason: {e}")

        logger.info("Restore complete.")

    def view_backups(self, ctx):
        """Display a list of available backups that were found in the backup folder."""
        cli_context: CliContext = ctx.obj
        logger.info("Displaying all locally-available backups.")

        backup_dir: Path = cli_context.backup_dir

        files = [
            os.path.join(path[len(str(backup_dir)) :].lstrip("/"), name)  # noqa: E203
            for path, subdirs, files in os.walk(backup_dir)
            for name in files
        ]

        backup_dir_files = sorted(
            files,
            reverse=True,
        )
        for backup in backup_dir_files:
            print(backup)

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

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
                # On the rare occasion that a leading "/" sneaks in remove it otherwise restore will try to un-tar to "/"
                member.path = member.path.strip("/")
                yield member

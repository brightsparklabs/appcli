#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Manages configuration.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# vendor libraries
from jinja2 import StrictUndefined, Template

from appcli.crypto import crypto

# local libraries
from appcli.crypto.crypto import decrypt_values_in_file
from appcli.functions import error_and_exit, print_header
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.variables_manager import VariablesManager

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

METADATA_FILE_NAME = "metadata-configure-apply.json"
""" Name of the file holding metadata from running a configure (relative to the generated configuration directory) """

# ------------------------------------------------------------------------------
# PUBLIC CLASSES
# ------------------------------------------------------------------------------


class ConfigurationManager:
    """Manages the configuration of the application. Handles initialisation, settings changes, migration to new versions, etc."""

    def __init__(self, cli_context: CliContext, configuration: Configuration):
        self.cli_context = cli_context
        self.config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            cli_context.configuration_dir
        )
        self.cli_configuration: Configuration = configuration
        self.variables_manager: VariablesManager = cli_context.get_variables_manager()

    def initialise_configuration(self):
        """Initialises the configuration repository"""

        if not self.config_repo.is_repo_on_master_branch():
            error_and_exit(
                "Cannot initialise configuration, repo is not on master branch."
            )

        # Populate with new configuration
        self.__create_new_configuration_branch_and_files()

    def apply_configuration_changes(self, message: str):
        """Applies the current configuration settings to templates to generate application files.

        Args:
            message (str): The message associated with the changes this applies.
        """

        if self.config_repo.is_repo_on_master_branch():
            error_and_exit("Cannot apply configuration, repo is on master branch.")

        # Commit changes to the configuration repository
        self.config_repo.commit_changes(message)

        # Re-generated generated configuration
        self.__regenerate_generated_configuration()

    def migrate_configuration(self):
        """Migrates the configuration version to the current application version"""

        if self.config_repo.is_repo_on_master_branch():
            error_and_exit("Cannot migrate, repo is on master branch.")

        config_version: str = self.config_repo.get_repository_version()
        app_version: str = self.cli_context.app_version

        # If the configuration version matches the application version, no migration is required.
        if config_version == app_version:
            logger.info(
                f"Migration not required. Config version [{config_version}] matches application version [{app_version}]"
            )
            return

        logger.info(
            f"Migrating configuration version [{config_version}] to match application version [{app_version}]"
        )

        app_version_branch: str = self.config_repo.generate_branch_name(app_version)
        if self.config_repo.does_branch_exist(app_version_branch):
            # If the branch already exists, then this version has previously been installed.

            logger.warning(
                f"Version [{app_version}] of this application was previously installed. Rolling back to previous configuration. Manual remediation may be required."
            )

            # Switch to that branch, no further migration steps will be taken. This is effectively a roll-back.
            self.config_repo.checkout_existing_branch(app_version_branch)
            return

        # Get the stack-settings file contents if it exists
        stack_config_file = self.cli_context.get_stack_configuration_file()
        stack_settings_exists_pre_migration = stack_config_file.is_file()
        current_stack_settings_variables = (
            stack_config_file.read_text()
            if stack_settings_exists_pre_migration
            else None
        )

        # Migrate the current configuration variables
        current_variables = self.variables_manager.get_all_variables()

        # Compare migrated config to the 'clean config' of the new version, and make sure all variables have been set and are the same type.
        key_file = self.cli_context.get_key_file()
        clean_new_version_variables = VariablesManager(
            self.cli_configuration.seed_app_configuration_file, key_file=key_file
        ).get_all_variables()

        migrated_variables = self.cli_configuration.hooks.migrate_variables(
            self.cli_context,
            current_variables,
            config_version,
            clean_new_version_variables,
        )

        if not self.cli_configuration.hooks.is_valid_variables(
            self.cli_context, migrated_variables, clean_new_version_variables
        ):
            error_and_exit(
                "Migrated variables did not pass application-specific variables validation function."
            )

        baseline_template_overrides_dir = (
            self.cli_context.get_baseline_template_overrides_dir()
        )
        override_backup_dir: Path = self.__backup_directory(
            baseline_template_overrides_dir
        )

        configurable_templates_dir = self.cli_context.get_configurable_templates_dir()
        configurable_templates_backup_dir = self.__backup_directory(
            configurable_templates_dir
        )

        # Backup and remove the existing generated config dir since it's now out of date
        self.__backup_and_create_new_generated_config_dir(config_version)

        # Initialise the new configuration branch and directory with all new files
        self.__create_new_configuration_branch_and_files()

        self.__overwrite_directory(override_backup_dir, baseline_template_overrides_dir)
        if self.__directory_is_not_empty(baseline_template_overrides_dir):
            logger.warning(
                f"Overrides directory [{baseline_template_overrides_dir}] is non-empty, please check for compatibility of overridden files"
            )

        self.__overwrite_directory(
            configurable_templates_backup_dir, configurable_templates_dir
        )
        if self.__directory_is_not_empty(configurable_templates_dir):
            logger.warning(
                f"Configurable templates directory [{configurable_templates_dir}] is non-empty, please check for compatibility"
            )

        # Write out 'migrated' variables file
        self.variables_manager.set_all_variables(migrated_variables)

        # If stack settings existed pre-migration, then replace the default with the existing settings
        if stack_settings_exists_pre_migration:
            logger.warning(
                "Stack settings file was copied directly from previous version, please check for compatibility"
            )
            stack_config_file.write_text(current_stack_settings_variables)

        # Commit the new variables file
        self.config_repo.commit_changes(
            f"Migrated variables file from version [{config_version}] to version [{app_version}]"
        )

    def get_variable(self, variable: str, decrypt: bool = False):
        return self.variables_manager.get_variable(variable, decrypt=decrypt)

    def set_variable(self, variable: str, value: any):
        return self.variables_manager.set_variable(variable, value)

    def get_stack_variable(self, variable: str):
        return self.variables_manager.get_stack_variable(variable)

    def __create_new_configuration_branch_and_files(self):
        app_version: str = self.cli_context.app_version
        app_version_branch: str = self.config_repo.generate_branch_name(app_version)

        # Try to get an existing key
        path_to_key_file = self.cli_context.get_key_file()
        key_file_contents = None
        if path_to_key_file.exists():
            key_file_contents = path_to_key_file.read_bytes()

        # Create a new branch for this current application version
        self.config_repo.checkout_new_branch_from_master(app_version_branch)

        # If the keyfile already exists, re-use it across branches. Otherwise create a new keyfile.
        if key_file_contents:
            logger.debug("Found existing key. Copied to new configuration branch")
            path_to_key_file.write_bytes(key_file_contents)
        else:
            logger.debug("No key found. Creating new key file")
            crypto.create_and_save_key(path_to_key_file)

        # Seed the configuration directory
        self.__seed_configuration_dir()

        # Commit the changes, and tag as $VERSION
        self.config_repo.commit_changes(
            f"Default configuration at version [{app_version}]"
        )

        self.config_repo.tag_current_commit(f"{app_version}")

    def __seed_configuration_dir(self):
        """Seed the raw configuration into the configuration directory"""
        print_header("Seeding configuration directory ...")

        logger.debug("Copying app configuration file ...")
        seed_app_configuration_file = self.cli_configuration.seed_app_configuration_file
        if not seed_app_configuration_file.is_file():
            error_and_exit(
                f"Seed file [{seed_app_configuration_file}] is not valid. Release is corrupt."
            )

        # Create the configuration directory and copy in the app config file
        target_app_configuration_file = self.cli_context.get_app_configuration_file()
        logger.debug(
            "Copying app configuration file to [%s] ...", target_app_configuration_file
        )
        os.makedirs(target_app_configuration_file.parent, exist_ok=True)
        shutil.copy2(seed_app_configuration_file, target_app_configuration_file)

        stack_configuration_file = self.cli_configuration.stack_configuration_file
        target_stack_configuration_file = (
            self.cli_context.get_stack_configuration_file()
        )
        # Copy in the stack configuration file
        if stack_configuration_file.is_file():
            shutil.copy2(stack_configuration_file, target_stack_configuration_file)

        # Create the configurable templates directory
        logger.debug("Copying configurable templates ...")
        configurable_templates_dir = self.cli_context.get_configurable_templates_dir()
        configurable_templates_dir.mkdir(parents=True, exist_ok=True)
        seed_configurable_templates_dir = (
            self.cli_configuration.configurable_templates_dir
        )

        if seed_configurable_templates_dir is None:
            logger.debug("No configurable templates directory defined")
            return

        if not seed_configurable_templates_dir.is_dir():
            error_and_exit(
                f"Seed templates directory [{seed_configurable_templates_dir}] is not valid. Release is corrupt."
            )

        # Copy each seed file to the configurable templates directory
        for source_file in seed_configurable_templates_dir.glob("**/*"):
            logger.debug(source_file)
            relative_file = source_file.relative_to(seed_configurable_templates_dir)
            target_file = configurable_templates_dir.joinpath(relative_file)

            if source_file.is_dir():
                logger.debug("Creating directory [%s] ...", target_file)
                target_file.mkdir(parents=True, exist_ok=True)
            else:
                logger.debug("Copying seed file to [%s] ...", target_file)
                shutil.copy2(source_file, target_file)

    def __regenerate_generated_configuration(self):
        """Generate the generated configuration files"""

        print_header("Generating configuration files")
        generated_configuration_dir = self.__backup_and_create_new_generated_config_dir(
            self.config_repo.get_repository_version()
        )

        logger.info("Generating configuration from default templates")
        self.__apply_templates_from_directory(
            self.cli_configuration.baseline_templates_dir, generated_configuration_dir
        )

        logger.info("Generating configuration from override templates")
        self.__apply_templates_from_directory(
            self.cli_context.get_baseline_template_overrides_dir(),
            generated_configuration_dir,
        )

        logger.info("Generating configuration from configurable templates")
        self.__apply_templates_from_directory(
            self.cli_context.get_configurable_templates_dir(),
            generated_configuration_dir,
        )

        files_to_decrypt = self.cli_configuration.decrypt_generated_files
        if len(files_to_decrypt) > 0:
            self.__decrypt_generated_files(
                self.cli_context.get_key_file(),
                self.cli_context.get_generated_configuration_dir(),
                files_to_decrypt,
            )

        # Copy the settings file that was used to generate the templates
        self.__copy_settings_files_to_generated_dir()

        # Generate the metadata file
        self.__generate_configuration_metadata_file()

        # By re-instantiating the 'GeneratedConfigurationGitRepository', we put
        # the generated config repo under version control.
        generated_config_repo = GeneratedConfigurationGitRepository(
            self.cli_context.get_generated_configuration_dir()
        )

        logger.debug(
            f"Generated configuration at [{generated_config_repo.get_repo_path()}]"
        )

    def __apply_templates_from_directory(
        self, template_path: Path, generated_configuration_dir: Path
    ):
        """Applies templates from a source directory to the generated directory

        Args:
            template_path (Path): directory to the templates
            generated_configuration_dir (Path): directory to output generated files
        """
        template_data = self.variables_manager.get_templating_configuration()
        for template_file in template_path.glob("**/*"):
            relative_file = template_file.relative_to(template_path)
            target_file = generated_configuration_dir.joinpath(relative_file)

            if template_file.is_dir():
                logger.debug("Creating directory [%s] ...", target_file)
                target_file.mkdir(parents=True, exist_ok=True)
                continue

            if template_file.suffix == ".j2":
                # parse jinja2 templates against configuration
                target_file = target_file.with_suffix("")
                logger.debug("Generating configuration file [%s] ...", target_file)
                self.__generate_from_template(
                    template_file,
                    target_file,
                    template_data,
                )
            else:
                logger.debug("Copying configuration file to [%s] ...", target_file)
                shutil.copy2(template_file, target_file)

    def __directory_is_not_empty(self, directory: Path) -> bool:
        """Checks if a directory is not empty.

        Returns:
            bool: Returns True if the directory exists and contains any files, otherwise False
        """
        if not os.path.exists(directory):
            return False

        files_in_directory = [i for i in os.listdir(directory) if i != ".gitkeep"]

        return len(files_in_directory) > 0

    def __backup_directory(self, directory_to_backup: Path) -> Path:
        """Backup a specified directory to a temporary directory

        Args:
            directory_to_backup (Path): The directory to backup

        Returns:
            Path: The directory to the temporary backup, or None if the directory to backup doesn't exist
        """
        if not os.path.isdir(directory_to_backup):
            return None

        temp_dir = Path(tempfile.mkdtemp())

        # Due to a limitation with 'copytree', it fails to copy if the root directory exists
        # before copying. So we delete the temp dir prior to copying.
        os.rmdir(temp_dir)
        shutil.copytree(str(directory_to_backup), str(temp_dir), dirs_exist_ok=True)

        return temp_dir

    def __overwrite_directory(self, source_dir: Path, target_dir: Path):
        """Copies the contents of one directory to another, overwriting any existing contents.
        If the source directory doesn't exist, the target directory will not either.

        Args:
            source_dir (Path): Source directory
            target_dir (Path): Target directory
        """
        logger.debug(f"Copying from {source_dir} to {target_dir}")

        # If the target directory exists, delete all contents
        # This is achieved by deleting the folder and re-creating it
        # This is easier than iterating through the contents and deleting those
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)

        # If the source directory doesn't exist, or isn't a directory, then do not create the
        # target directory
        if source_dir is None or not source_dir.exists() or not source_dir.is_dir():
            return

        os.mkdir(target_dir)
        shutil.copytree(str(source_dir), str(target_dir), dirs_exist_ok=True)

    def __backup_and_create_new_generated_config_dir(
        self, current_config_version
    ) -> Path:
        """Backup the generated configuration dir, and delete all its contents

        Returns:
            Path: path to the generated configuration dir
        """
        generated_configuration_dir = self.cli_context.get_generated_configuration_dir()
        return self.__backup_and_create_new_directory(
            generated_configuration_dir, current_config_version
        )

    def __generate_from_template(
        self, template_file: Path, target_file: Path, variables: dict
    ):
        """
        Generate configuration file from the specified template file using
        the supplied variables.

        Args:
            template_file (Path): Template used to generate the file.
            target_file (Path): Location to write the generated file to.
            variables (dict): Variables used to populate the template.
        """
        template = Template(
            template_file.read_text(),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        try:
            output_text = template.render(variables)
            target_file.write_text(output_text)
        except Exception as e:
            error_and_exit(
                f"Could not generate file from template. The configuration file is likely missing a setting: {e}"
            )

    def __decrypt_generated_files(
        self, key_file: Path, generated_config_dir: Path, files: Iterable[str]
    ):
        """
        Decrypts the specified files in the generated configuration
        directory. The current encrypted version will be overwritten by the
        decrypted version.

        Args:
            key_file (Path): Key file to use when decrypting.
            generated_config_dir (Path): Path to the generated configuration directory.
            files (Iterable[str]): Relative path to the files to decrypt. Resolved against the generated configuration directory.
        """
        for relative_file in files:
            # decrypt and overwrite the file
            target_file = generated_config_dir.joinpath(relative_file)
            logger.debug("Decrypting [%s] ...", target_file)
            decrypt_values_in_file(target_file, target_file, key_file)

    def __copy_settings_files_to_generated_dir(self):
        """Copies the current settings file and encryption key to the generated directory as a record of what configuration
        was used to generate those files.
        """
        logger.debug(
            "Copying applied settings file to generated configuration directory"
        )

        generated_config_dir = self.cli_context.get_generated_configuration_dir()

        applied_configuration_file = generated_config_dir.joinpath(
            self.cli_context.get_app_configuration_file().name
        )
        shutil.copy2(
            self.cli_context.get_app_configuration_file(), applied_configuration_file
        )

        logger.debug("Copying applied key file to generated configuration directory")
        applied_key_file = generated_config_dir.joinpath(
            self.cli_context.get_key_file().name
        )
        shutil.copy2(self.cli_context.get_key_file(), applied_key_file)

        logger.debug(
            "Applied settings and key file written to [%s] and [%s]",
            applied_configuration_file,
            applied_key_file,
        )

    def __generate_configuration_metadata_file(self):
        record = {
            "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "generated_from_commit": self.config_repo.get_current_commit_hash(),
        }
        configuration_record_file = self.__get_generated_configuration_metadata_file(
            self.cli_context
        )
        # Overwrite the existing generated configuration metadata record file
        configuration_record_file.write_text(
            json.dumps(record, indent=2, sort_keys=True)
        )
        logger.debug("Configuration record written to [%s]", configuration_record_file)

    def __backup_and_create_new_directory(
        self, source_dir: Path, additional_filename_descriptor: str = "backup"
    ) -> Path:
        """Backs up a directory to a tar gzipped file with the current datetimestamp,
        deletes the existing directory, and creates a new empty directory in its place

        Args:
            source_dir (Path): Path to the directory to backup and delete
            additional_filename_descriptor (str, optional): an additional identifier to put into
                the new tgz filename. If not supplied, defaults to 'backup'.
        """

        if os.path.exists(source_dir) and os.listdir(source_dir):
            # The datetime is accurate to seconds (microseconds was overkill), and we remove
            # colon (:) because `tar tvf` doesn't like filenames with colons
            current_datetime = (
                datetime.now().replace(microsecond=0).isoformat().replace(":", "")
            )
            # We have to do a replacement in case it has a slash in it, which causes the
            # creation of the tar file to fail
            clean_additional_filename_descriptor = (
                additional_filename_descriptor.replace("/", "-")
            )
            basename = os.path.basename(source_dir)
            output_filename = os.path.join(
                os.path.dirname(source_dir),
                Path(".generated-archive/"),
                f"{basename}_{clean_additional_filename_descriptor}_{current_datetime}.tgz",
            )

            # Create the backup
            logger.debug(f"Backing up directory [{source_dir}] to [{output_filename}]")
            output_dir = os.path.dirname(output_filename)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            with tarfile.open(output_filename, "w:gz") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))

            # Ensure the backup has been successfully created before deleting the existing generated configuration directory
            if not os.path.exists(output_filename):
                error_and_exit(
                    f"Current generated configuration directory backup failed. Could not write out file [{output_filename}]."
                )

            # Remove the existing directory
            shutil.rmtree(source_dir, ignore_errors=True)
            logger.debug(
                f"Deleted previous generated configuration directory [{source_dir}]"
            )

        source_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Created clean directory [{source_dir}]")

        return source_dir

    def __get_generated_configuration_metadata_file(
        self, cli_context: CliContext
    ) -> Path:
        """Get the path to the generated configuration's metadata file

        Args:
            cli_context (CliContext): The current CLI context.

        Returns:
            Path: the path to the metadata file
        """
        generated_configuration_dir = cli_context.get_generated_configuration_dir()
        return generated_configuration_dir.joinpath(METADATA_FILE_NAME)

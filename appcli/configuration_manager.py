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
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# vendor libraries
from jinja2 import StrictUndefined, Template


# local libraries
from appcli.crypto.crypto import decrypt_values_in_file
from appcli.functions import (
    error_and_exit,
    print_header,
    execute_validation_functions,
)
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
    confirm_config_dir_exists,
    confirm_config_dir_not_exists,
    confirm_config_dir_exists_and_is_not_dirty,
    confirm_not_on_master_branch,
    confirm_generated_config_dir_exists,
    confirm_generated_config_dir_exists_and_is_not_dirty,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.variables_manager import VariablesManager

from appcli.crypto import crypto

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
        self.cli_configuration: Configuration = configuration

    def initialise_configuration(self):
        """Initialises the configuration repository
        """

        self.__pre_init_validation(self.cli_context)

        # Initialise the empty repo
        config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            self.cli_context
        )

        # Populate with new configuration
        self.__create_new_configuration_branch_and_files(config_repo)

    def __pre_init_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for 'configure init'.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.debug("Checking system configuration is valid before initialising ...")

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=[confirm_config_dir_not_exists],
            force=False,
        )

        logger.debug("System configuration is valid for initialisation")

    def apply_configuration_changes(self, message: str, force: bool = False):
        """Applies the current configuration settings to templates to generate application files.

        Args:
            message (str): the message associated with the changes this applies
            force (bool): If True, only warns on validation failures, rather than exiting
        """

        self.__pre_apply_validation(self.cli_context, force)

        config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            self.cli_context
        )

        # Commit changes to the configuration repository
        config_repo.commit_changes(message)

        generated_config_repo = self.__regenerate_generated_configuration(config_repo)
        logger.debug(
            f"Initialised generated configuration at [{generated_config_repo.repo.working_dir}]"
        )

    def __pre_apply_validation(self, cli_context: CliContext, force: bool = False):
        """Ensures the system is in a valid state to do an 'apply' on the configuration

        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If True, only warns on validation failures, rather than exiting
        """
        logger.debug("Checking system configuration is valid before 'apply' ...")

        # If the config dir doesn't exist, or we're on the master branch, we cannot apply
        must_succeed_checks = [
            confirm_config_dir_exists,
            confirm_not_on_master_branch,
        ]

        should_succeed_checks = []

        # If the generated configuration directory exists, test it for 'dirtiness'.
        # Otherwise the generated config doesn't exist, so the directories are 'clean'.
        try:
            confirm_generated_config_dir_exists(cli_context)
        except Exception:
            # If the confirm fails, then we just pass as this is an expected error
            pass
        else:
            # If the generated config is dirty, or not running against current config, warn before overwriting
            should_succeed_checks = [
                confirm_generated_config_dir_exists_and_is_not_dirty,
                confirm_generated_configuration_is_using_current_configuration,
            ]

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=must_succeed_checks,
            should_succeed_checks=should_succeed_checks,
            force=force,
        )

        logger.debug("System configuration is valid for 'apply' function")

    def migrate_configuration(
        self, ignore_variables_migration_structural_errors: bool = False
    ):
        """Migrates the configuration version to the current application version

        Args:
            ignore_variables_migration_structural_errors (bool, optional): If True, will ignore stuctural validation errors in the application-migrated variables. Defaults to False.
        """

        self.__pre_migrate_validation(self.cli_context)

        config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            self.cli_context
        )
        config_version: str = config_repo.get_current_branch_name()
        app_version: str = self.__get_app_version()

        # If the configuration version matches the application version, no migration is required.
        if config_version == app_version:
            logger.info(
                f"Migration not required. Config version [{config_version}] matches application version [{app_version}]"
            )
            return

        logger.info(
            f"Migrating configuration version [{config_version}] to match application version [{app_version}]"
        )

        if config_repo.does_branch_exist(app_version):
            # If the branch already exists, then this version has previously been installed.

            logger.warn(
                f"Version [{app_version}] of this application was previously installed. Rolling back to previous configuration. Manual remediation may be required."
            )

            # Switch to that branch, no further migration steps will be taken. This is effectively a roll-back.
            config_repo.checkout_existing_branch(app_version)
            return

        # Migrate the current configuration variables
        current_variables = self.get_variables_manager().get_all_variables()

        # Compare migrated config to the 'clean config' of the new version, and make sure all variables have been set and are the same type.
        clean_new_version_variables = VariablesManager(
            self.cli_configuration.seed_app_configuration_file
        ).get_all_variables()

        migrated_variables = self.cli_configuration.hooks.migrate_variables(
            current_variables, config_version, clean_new_version_variables
        )

        if not self.cli_configuration.hooks.is_valid_variables(
            migrated_variables, clean_new_version_variables
        ):
            error_and_exit(
                f"Migrated variables did not pass application-specific variables validation function."
            )

        # Get the diff of template files from 'base' of branch (i.e. the tag which matches the branch name) to current HEAD of the branch
        diff_data = config_repo.get_diff_to_tag(config_version, "templates/")

        # Backup and remove the existing generated config dir since it's now out of date
        self.__backup_and_create_new_generated_config_dir(config_version)

        # Initialise the new configuration branch and directory with all new files
        self.__create_new_configuration_branch_and_files(config_repo)

        # Write out 'migrated' variables file
        self.get_variables_manager().set_all_variables(migrated_variables)

        # Commit the new variables file
        config_repo.commit_changes(
            f"Migrated variables file from version [{config_version}] to version [{app_version}]"
        )

        if diff_data:
            logger.warn(
                "Changes to default templates have been made. These changes need to be re-applied manually."
            )
            logger.warn(
                f"Diff of all templates since default of version [{config_version}]:\n{diff_data}"
            )
            current_datetime = (
                datetime.now().replace(microsecond=0).isoformat().replace(":", "")
            )
            self.cli_context.get_configuration_metadata_dir().mkdir(
                parents=True, exist_ok=True
            )
            diff_out_file = self.cli_context.get_configuration_metadata_dir().joinpath(
                f"template-changes-from-default_{config_version}_{current_datetime}.diff"
            )
            diff_out_file.write_text(diff_data)
            logger.warn(
                f"These diffs have also been written out to file: [{diff_out_file}]"
            )
        else:
            logger.info(
                "No changes to default templates detected, no manual fixes are required."
            )

    def __pre_migrate_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for migration.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.debug("Checking system configuration is valid before migration ...")

        should_succeed_checks = []

        # If the generated configuration directory exists, test it for 'dirtiness'.
        # Otherwise the generated config doesn't exist, so the directories are 'clean'.
        try:
            confirm_generated_config_dir_exists(cli_context)
            # If the generated config is dirty, or not running against current config, warn before overwriting
            should_succeed_checks = [
                confirm_generated_config_dir_exists_and_is_not_dirty,
                confirm_generated_configuration_is_using_current_configuration,
            ]
        except Exception:
            # If the confirm fails, then we just pass as this is an expected error
            pass

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=[confirm_config_dir_exists_and_is_not_dirty],
            should_succeed_checks=should_succeed_checks,
        )

        logger.debug("System configuration is valid for migration.")

    def get_variables_manager(self):
        app_config_file = self.cli_context.get_app_configuration_file()
        return VariablesManager(app_config_file)

    def __create_new_configuration_branch_and_files(
        self, config_repo: ConfigurationGitRepository
    ):

        app_version: str = self.__get_app_version()

        # Try to get an existing key
        path_to_key_file = self.cli_context.get_key_file()
        key_file_contents = None
        if path_to_key_file.exists():
            key_file_contents = path_to_key_file.read_bytes()

        # Create a new branch for this current application version
        config_repo.checkout_new_branch_from_master(app_version)

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
        config_repo.commit_changes(f"Default configuration at version [{app_version}]")

        config_repo.tag_current_commit(f"{app_version}")

    def __get_app_version(self) -> str:
        """Get the target application version, which is the version of the application
        which is currently running in the Docker container.

        Returns:
            str: version of the application according to the Docker container this script is running in.
        """
        logger.error(
            "Currently getting app_version from datetime. This MUST be rolled back."
        )
        return self.cli_context.app_version

    def __seed_configuration_dir(self):
        """Seed the raw configuration into the configuration directory
        """
        print_header("Seeding configuration directory ...")

        logger.info("Copying app configuration file ...")
        seed_app_configuration_file = self.cli_configuration.seed_app_configuration_file
        if not seed_app_configuration_file.is_file():
            error_and_exit(
                f"Seed file [{seed_app_configuration_file}] is not valid. Release is corrupt."
            )

        target_app_configuration_file = self.cli_context.get_app_configuration_file()
        logger.debug(
            "Copying app configuration file to [%s] ...", target_app_configuration_file
        )
        target_app_configuration_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed_app_configuration_file, target_app_configuration_file)

        logger.info("Copying templates ...")
        templates_dir = self.cli_context.get_templates_dir()
        templates_dir.mkdir(parents=True, exist_ok=True)
        seed_templates_dir = self.cli_configuration.seed_templates_dir
        if not seed_templates_dir.is_dir():
            error_and_exit(
                f"Seed templates directory [{seed_templates_dir}] is not valid. Release is corrupt."
            )

        for source_file in seed_templates_dir.glob("**/*"):
            logger.info(source_file)
            relative_file = source_file.relative_to(seed_templates_dir)
            target_file = templates_dir.joinpath(relative_file)

            if source_file.is_dir():
                logger.debug("Creating directory [%s] ...", target_file)
                target_file.mkdir(parents=True, exist_ok=True)
            else:
                logger.debug("Copying seed file to [%s] ...", target_file)
                shutil.copy2(source_file, target_file)

    def __regenerate_generated_configuration(
        self, config_repo: ConfigurationGitRepository
    ) -> GeneratedConfigurationGitRepository:
        """Generate the generated configuration files
        """

        print_header(f"Generating configuration files")
        generated_configuration_dir = self.__backup_and_create_new_generated_config_dir(
            config_repo.get_current_branch_name()
        )

        for template_file in self.cli_context.get_templates_dir().glob("**/*"):
            relative_file = template_file.relative_to(
                self.cli_context.get_templates_dir()
            )
            target_file = generated_configuration_dir.joinpath(relative_file)

            if template_file.is_dir():
                logger.debug("Creating directory [%s] ...", target_file)
                target_file.mkdir(parents=True, exist_ok=True)
                continue

            if template_file.suffix == ".j2":
                # parse jinja2 templates against configuration
                target_file = target_file.with_suffix("")
                logger.info("Generating configuration file [%s] ...", target_file)
                self.__generate_from_template(
                    template_file,
                    target_file,
                    self.get_variables_manager().get_all_variables(),
                )
            else:
                logger.info("Copying configuration file to [%s] ...", target_file)
                shutil.copy2(template_file, target_file)

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
        self.__generate_configuration_metadata_file(config_repo)

        # Put the generated config repo under version control
        generated_config_repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
            self.cli_context
        )

        logger.info("Generated configuration files successfully ...")
        return generated_config_repo

    def __backup_and_create_new_generated_config_dir(
        self, current_config_version
    ) -> Path:
        """Backup the generated configuration dir, and create a new one

        Returns:
            Path: path to the clean generated configuration dir
        """
        generated_configuration_dir = self.cli_context.get_generated_configuration_dir()
        return backup_and_create_new_directory(
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

    def __generate_configuration_metadata_file(
        self, config_repo: ConfigurationGitRepository
    ):
        record = {
            "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "generated_from_commit": config_repo.get_current_commit_hash(),
        }
        configuration_record_file = get_generated_configuration_metadata_file(
            self.cli_context
        )
        # Overwrite the existing generated configuration metadata record file
        configuration_record_file.write_text(
            json.dumps(record, indent=2, sort_keys=True)
        )
        logger.debug("Configuration record written to [%s]", configuration_record_file)


# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


def backup_and_create_new_directory(
    source_dir: Path, additional_filename_descriptor: str = "backup"
) -> Path:
    """Backs up a directory to a tar gzipped file with the current datetimestamp,
    and deletes the existing directory

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
        clean_additional_filename_descriptor = additional_filename_descriptor.replace(
            "/", "-"
        )
        basename = os.path.basename(source_dir)
        output_filename = os.path.join(
            os.path.dirname(source_dir),
            f"{basename}_{clean_additional_filename_descriptor}_{current_datetime}.tgz",
        )

        # Create the backup
        logger.info(f"Backing up directory [{source_dir}] to [{output_filename}]")
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

        # Ensure the backup has been successfully created before deleting the existing generated configuration directory
        if not os.path.exists(output_filename):
            error_and_exit(
                f"Current generated configuration directory backup failed. Could not write out file [{output_filename}]."
            )

        # Remove the existing directory
        shutil.rmtree(source_dir, ignore_errors=True)
        logger.info(
            f"Deleted previous generated configuration directory [{source_dir}]"
        )

    source_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created clean directory [{source_dir}]")

    return source_dir


def get_generated_configuration_metadata_file(cli_context: CliContext) -> Path:
    """Get the path to the generated configuration's metadata file

    Args:
        cli_context (CliContext): the current cli context

    Returns:
        Path: the path to the metadata file
    """
    generated_configuration_dir = cli_context.get_generated_configuration_dir()
    return generated_configuration_dir.joinpath(METADATA_FILE_NAME)


def confirm_generated_configuration_is_using_current_configuration(
    cli_context: CliContext,
):
    """Confirm that the generated configuration directory was generated from the current state configuration directory.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if metadata file not found, or generated config is out of sync with config.
    """
    confirm_config_dir_exists(cli_context)
    metadata_file = get_generated_configuration_metadata_file(cli_context)
    if not os.path.isfile(metadata_file):
        raise Exception(
            f"Could not find a metadata file at [{metadata_file}]. Please run `configure apply`"
        )

    with open(metadata_file, "r") as f:
        metadata = json.load(f)
        logger.debug("Found metadata from generated configuration: %s", metadata)

    generated_commit_hash = metadata["generated_from_commit"]
    configuration_commit_hash = ConfigurationGitRepository(
        cli_context
    ).get_current_commit_hash()
    if generated_commit_hash != configuration_commit_hash:
        logger.debug(
            "Mismatched hash. Generated configuration hash [%s] does not match configuration hash [%s]",
            generated_commit_hash,
            configuration_commit_hash,
        )
        raise Exception(
            "Generated configuration is out of sync with raw configuration. Please run `configure apply`."
        )

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
from functools import reduce
from pathlib import Path
from typing import Dict, Iterable

# vendor libraries
from ruamel.yaml import YAML
from jinja2 import StrictUndefined, Template


# local libraries
from appcli.crypto.crypto import decrypt_values_in_file
from appcli.functions import (
    error_and_exit,
    print_header,
)
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

from appcli.crypto import crypto

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

METADATA_FILE_NAME = "metadata-configure-apply.json"
""" Name of the file holding metadata from running a configure (relative to the generated configuration directory) """

# ------------------------------------------------------------------------------
# INTERNAL CLASSES
# ------------------------------------------------------------------------------


class SettingsManager:
    """Manages the configuration"""

    def __init__(self, configuration_file):
        """Creates a manager for the specified file

        Args:
            configuration_file (str): Path to the configuration file to manage
        """
        self.configuration_file = Path(configuration_file)
        data = self.configuration_file.read_text(encoding="utf-8")
        self.yaml = YAML()
        self.configuration = self.yaml.load(data)

    def get(self, path):
        """Gets a value from the configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
        """
        try:
            return reduce(lambda e, k: e[k], path.split("."), self.configuration)
        except Exception:
            return ""

    def get_all(self):
        return self.configuration

    def set(self, path, value):
        """Sets a value in the configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
            value: value for the setting
        """
        path_elements = path.split(".")
        parent_path = path_elements[:-1]

        # ensure parent path exists
        def ensure_path(parent, child):
            if child not in parent:
                parent[child] = {}
            return parent[child]

        reduce(ensure_path, parent_path, self.configuration)

        # set the value
        parent_element = reduce(lambda e, k: e[k], parent_path, self.configuration)
        parent_element[path_elements[-1]] = value

        self.__save()

    def set_all(self, variables: Dict):
        """Sets all values in the configuration

        Args:
            variables (Dict): the variables to set
        """
        self.configuration = variables
        self.__save()

    def __save(self):
        """Saves the configuration"""
        full_path = self.configuration_file.absolute().as_posix()
        logger.info(f"Saving configuration to [{full_path}] ...")
        with open(full_path, "w") as config_file:
            self.yaml.dump(self.configuration, config_file)


# ------------------------------------------------------------------------------
# PUBLIC CLASSES
# ------------------------------------------------------------------------------


class ConfigurationManager:
    """Manages the configuration of the application. Handles initialisation, settings changes, migration to new versions, etc."""

    def __init__(self, cli_context: CliContext, configuration: Configuration):
        self.cli_context = cli_context
        self.cli_configuration: Configuration = configuration

        # Get the SettingsManager for the current settings file
        self.app_config_file = self.cli_context.get_app_configuration_file()
        self.settings_manager: SettingsManager = SettingsManager(self.app_config_file)

        self.config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            self.cli_context
        )
        self.generated_config_repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
            self.cli_context
        )

    def init(self):
        """Initialises the configuration repository
        """
        app_version: str = self.cli_context.app_version

        # Initialise the empty repo
        self.config_repo.init()

        # Create an encryption key and the .gitignore, and commit them
        crypto.create_and_save_key(self.cli_context.get_key_file())
        self.config_repo.set_gitignore([".generated*"])
        self.config_repo.commit_changes("[autocommit] Initialised repository")

        # Create a new branch for this current application version
        self.config_repo.checkout_new_branch(app_version)

        # Seed the configuration directory
        self.__seed_configuration_dir()

        # Commit the changes, and tag as $VERSION
        self.config_repo.commit_changes(
            f"Default configuration at version [{app_version}]"
        )
        self.config_repo.tag_current_commit(
            app_version
        )  # TODO: Possibly remove. Tag may be unnecessary

    def migrate(self, ignore_settings_migration_structural_errors: bool = False):
        """Migrates the configuration version to the current application version
        """

        # TODO: Test and confirm this works as expected.

        config_version: str = self.__get_config_version()
        app_version: str = self.__get_app_version()

        logger.info(
            f"Migrating configuration version [{config_version}] to match application version [{app_version}]"
        )

        # If the configuration version matches the application version, no migration is required.
        if config_version == app_version:
            logger.info("Migration not required.")
            return

        # TODO: Should we have a prompt to confirm that the user definitely wants to migrate from X version to Y version? Include a '-y' or '--yes' option to skip the prompt.

        if self.config_repo.does_branch_exist(app_version):
            # If the branch already exists, then this version has previously been installed.

            # TODO: Handle the case where it was previously installed, but we want multiple versions of a single version. e.g. v1-a, v1-b, v1-c
            logger.warn(
                f"Version [{app_version}] of this application was previously installed. Rolling back to previous configuration. Manual remediation may be required."
            )

            # Switch to that branch, no further migration steps will be taken. This is effectively a roll-back.
            self.config_repo.checkout_existing_branch(app_version)

            return

        # Installing a version which has not previously been installed.

        # Read the current configuration variables
        current_variables = self.get_all()

        # Delegate migration to the application callback function
        migrated_variables = self.cli_configuration.hooks.migrate_variables(
            current_variables, self.__get_config_version()
        )

        # Get the 'clean settings' of the new application
        clean_new_version_variables = SettingsManager(
            self.cli_configuration.seed_app_configuration_file
        ).get_all()

        # Compare migrated config to the 'clean config' of the new version, and make sure all variables have been set and are the same type.
        # TODO: Should we be comparing the entire Dict or just a slice of it? We should probably ignore a 'custom'-type block of variables
        if not self.__are_dicts_matching_structure(
            migrated_variables, clean_new_version_variables
        ):
            error_message: str = "Migrated settings structure does not match structure of clean structure."
            if ignore_settings_migration_structural_errors:
                logger.warn(
                    f"{error_message} Settings may need to be manually modified to fit expected structure."
                )
            else:
                error_and_exit(f"{error_message} Cancelling migration.")

        # Change branch to the clean 'master' branch
        self.config_repo.checkout_master_branch()

        # Copy over new version configuration files (re-seed)
        self.__seed_configuration_dir()

        # Create new branch, named after the version being deployed
        self.config_repo.checkout_new_branch(app_version)

        # Commit the default configuration and settings
        self.config_repo.commit_changes(
            f"Initialised configuration at version [{app_version}]"
        )

        # Write out 'migrated' variables file
        self.set_all(migrated_variables)

        # Commit the new variables file
        self.config_repo.commit_changes(
            f"Migrated variables file to version [{app_version}]"
        )

        # >> Now at v2 variables file. Still templates to go.

        # TODO: Diff all non-variables files (i.e. all templates files + w/e else) -> List of changed files, and their changes.

        # TODO: For each changed file, notify user that manual changes will need to be made to that template file. Provide diff.

        # TODO: Once all templates have been upgraded to v2, commit and done with migration!

    def apply(self, message: str):
        """Applies the current configuration settings to templates to generate application files.

        Args:
            message (str): the message associated with the changes this applies
        """
        # Commit changes to the configuration repository
        self.config_repo.commit_changes(message)

        # Generate new configuration files
        self.__generate_configuration_files(self.cli_configuration, self.cli_context)

        # Put the generated config repo under version control
        self.generated_config_repo.init()

    def get(self, path) -> str:
        """Gets a value from the configuration settings.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host

        Returns:
            str: current setting value
        """
        return self.settings_manager.get(path)

    def get_all(self) -> Dict:
        """Gets all configuration settings.

        Returns:
            Dict: current application settings
        """
        return self.settings_manager.get_all()

    def set(self, path, value):
        """Sets a value in the configuration settings.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
            value: value for the setting
        """
        self.settings_manager.set(path, value)

    def set_all(self, variables: Dict):
        """Sets all values in the configuration

        Args:
            variables (Dict): the variables to set
        """
        self.settings_manager.set_all(variables)

    def __get_app_version(self) -> str:
        """Get the target application version, which is the version of the application
        which is currently running in the Docker container.

        Returns:
            str: version of the application according to the Docker container this script is running in.
        """
        return self.cli_context.app_version

    def __get_config_version(self) -> str:
        """Get the current configuration repository's version

        Returns:
            str: version of the configuration repository
        """
        return self.config_repo.get_current_branch_name()

    def __are_dicts_matching_structure(self, dict_1: Dict, dict_2: Dict) -> bool:
        """Recursively checks if the keys of the first dictionary match the keys of the second.

        Args:
            migrated_variables (Dict): the migrated settings
            clean_new_version_variables (Dict): the clean version settings

        Returns:
            bool: True if the Dict keys match, else False
        """
        # If the set of keys isn't matching, these dicts don't "match"
        if dict_1.keys() != dict_2.keys():
            return False

        for key in dict_1.keys():
            # If the type of key_x in dict_1 doesn't match the type of the same key in dict_2, the
            # dicts don't match
            if not isinstance(dict_2[key], type(dict_1[key])):
                return False

            # If it's a dict type, recurse
            if isinstance(dict_1[key], dict):
                if not self.__are_dicts_matching_structure(dict_1[key], dict_2[key]):
                    return False

        return True

    def __seed_configuration_dir(self):
        """Seed the raw configuration into the configuration directory

        Args:
            cli_context (CliContext): the current cli context
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

    def __generate_configuration_files(
        self, configuration: Configuration, cli_context: CliContext
    ):
        """Generate the generated configuration files

        Args:
            configuration (Configuration): the current cli configuration
            cli_context (CliContext): the current cli context
        """
        print_header(f"Generating configuration files")
        generated_configuration_dir = cli_context.get_generated_configuration_dir()

        # If the generated configuration directory is not empty, back it up and delete
        if os.path.exists(generated_configuration_dir) and os.listdir(
            generated_configuration_dir
        ):
            self._backup_and_remove_directory(generated_configuration_dir)

        generated_configuration_dir.mkdir(parents=True, exist_ok=True)

        configuration_record_file = get_generated_configuration_metadata_file(
            cli_context
        )
        if os.path.exists(configuration_record_file):
            logger.info("Clearing successful configuration record ...")
            os.remove(configuration_record_file)
            logger.debug(
                f"Configuration record removed from [{configuration_record_file}]"
            )

        for template_file in cli_context.get_templates_dir().glob("**/*"):
            relative_file = template_file.relative_to(cli_context.get_templates_dir())
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
                    template_file, target_file, configuration.get_all()
                )
            else:
                logger.info("Copying configuration file to [%s] ...", target_file)
                shutil.copy2(template_file, target_file)

        files_to_decrypt = self.cli_configuration.decrypt_generated_files
        if len(files_to_decrypt) > 0:
            self.__decrypt_generated_files(
                cli_context.get_key_file(),
                cli_context.get_generated_configuration_dir(),
                files_to_decrypt,
            )

        self.__copy_settings_file_to_generated_dir(cli_context)

        logger.info("Saving successful configuration record ...")
        record = {
            "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "generated_from_commit": self.generated_config_repo.get_current_commit_hash(),
        }
        configuration_record_file.write_text(
            json.dumps(record, indent=2, sort_keys=True)
        )
        logger.debug("Configuration record written to [%s]", configuration_record_file)

    def _backup_and_remove_directory(self, source_dir: Path):
        """Backs up a directory to a tar gzipped file with the current datetimestamp,
        and deletes the existing directory

        Args:
            source_dir (Path): Path to the directory to backup and delete
        """

        # The datetime is accurate to seconds (microseconds was overkill), and we remove
        # colon (:) because `tar tvf` doesn't like filenames with colons
        current_datetime = (
            datetime.now().replace(microsecond=0).isoformat().replace(":", "")
        )
        basename = os.path.basename(source_dir)
        output_filename = os.path.join(
            os.path.dirname(source_dir), f"{basename}.{current_datetime}.tgz"
        )

        # Create the backup
        logger.info(
            f"Backing up current generated configuration directory [{source_dir}] to [{output_filename}]"
        )
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

    def __copy_settings_file_to_generated_dir(self, cli_context: CliContext):
        """Copies the current settings file to the generated directory as a record of what configuration
        was used to generate those files.

        Args:
            cli_context (CliContext): The context of the currently-running cli
        """
        logger.debug(
            "Copying applied settings file to generated configuration directory"
        )
        applied_configuration_file = cli_context.get_generated_configuration_dir().joinpath(
            cli_context.get_app_configuration_file().name
        )
        shutil.copy2(
            cli_context.get_app_configuration_file(), applied_configuration_file
        )

        logger.debug("Applied settings written to [%s]", applied_configuration_file)

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


# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


def get_generated_configuration_metadata_file(cli_context: CliContext) -> Path:
    """Get the path to the generated configuration's metadata file

    Args:
        cli_context (CliContext): the current cli context

    Returns:
        Path: the path to the metadata file
    """
    generated_configuration_dir = cli_context.get_generated_configuration_dir()
    return generated_configuration_dir.joinpath(METADATA_FILE_NAME)


def confirm_config_dir_exists(cli_context: CliContext):
    """Confirm that the configuration repository exists.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository does *not* exist.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if not config_repo.repo_exists():
        raise Exception(
            f"Configuration does not exist at [{config_repo.repo_path}]. Please run `configure init`."
        )


def confirm_config_dir_not_exists(cli_context: CliContext):
    """Confirm that the configuration repository does *not* exist.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository exists.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if config_repo.repo_exists():
        raise Exception(f"Configuration already exists at [{config_repo.repo_path}].")


def confirm_generated_config_dir_exists(cli_context: CliContext):
    """Confirm that the generated configuration repository exists.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the generated configuration repository does not exist.
    """
    generated_config_repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
        cli_context
    )
    if not generated_config_repo.repo_exists():
        raise Exception(
            f"Generated configuration does not exist at [{generated_config_repo.repo_path}]. Please run `configure apply`."
        )


def confirm_config_dir_is_not_dirty(cli_context: CliContext):
    """Confirm that the configuration repository has not been modified and not 'applied'.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository has been modified and not 'applied'.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    if config_repo.is_dirty(untracked_files=True):
        raise Exception(
            f"Configuration at [{config_repo.repo_path}]] contains changes which have not been applied. Please run `configure apply`."
        )


def confirm_generated_config_dir_is_not_dirty(cli_context: CliContext):
    """Confirm that the generated configuration repository has not been manually modified and not checked-in.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the generated configuration repository has been manually modified and not checked in.
    """
    generated_config_repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
        cli_context
    )
    if generated_config_repo.is_dirty(untracked_files=False):
        raise Exception(
            f"Generated configuration at [{generated_config_repo.repo_path}] has been manually modified."
        )


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
    metadata_file = get_generated_configuration_metadata_file(cli_context)
    if not os.path.isfile(metadata_file):
        raise Exception(
            f"Could not find a metadata file at [{metadata_file}]. Please run `configure apply`"
        )

    with open(metadata_file, "r") as f:
        metadata = json.load(f)
        logger.debug("Metadata from generated configuration: %s", metadata)

    generated_commit_hash = metadata["generated_from_commit"]
    configuration_commit_hash = ConfigurationGitRepository(
        cli_context
    ).get_current_commit_hash()
    if generated_commit_hash != configuration_commit_hash:
        logger.debug(
            "Generated configuration hash [%s] does not match configuration hash [%s]",
            generated_commit_hash,
            configuration_commit_hash,
        )
        raise Exception(
            "Generated configuration is out of sync with raw configuration. Please run `configure apply`."
        )


def confirm_config_version_matches_app_version(cli_context: CliContext):
    """Confirm that the configuration repository version matches the application version.
    If this fails, it will raise a general Exception with the error message.

    Args:
        cli_context (CliContext): the current cli context

    Raises:
        Exception: Raised if the configuration repository version doesn't match the application version.
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    config_version: str = config_repo.get_current_branch_name()

    app_version: str = cli_context.app_version

    if config_version != app_version:
        raise Exception(
            f"Configuration at [{config_repo.repo_path}] is using version [{config_version}] which is incompatible with current application version [{app_version}]. Migrate to this application version using 'migrate'."
        )


def confirm_not_on_master_branch(cli_context: CliContext):
    """Confirm that the configuration repository is not currently on the master branch.

    Args:
        cli_context (CliContext): the current cli context
    """
    config_repo: ConfigurationGitRepository = ConfigurationGitRepository(cli_context)
    config_version: str = config_repo.get_current_branch_name()

    if config_version == "master":
        raise Exception(
            f"Configuration at [{config_repo.repo_path}] is on the master branch."
        )

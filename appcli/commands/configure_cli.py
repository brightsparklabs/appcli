#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configures the system.
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
import click
from jinja2 import StrictUndefined, Template

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli.crypto.crypto import create_and_save_key, decrypt_values_in_file
from appcli.functions import (
    error_and_exit,
    get_generated_configuration_metadata_file,
    validate,
)
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
    confirm_config_dir_exists,
    confirm_config_dir_not_exists,
    confirm_generated_config_dir_exists,
    confirm_generated_config_dir_is_not_dirty,
    confirm_generated_configuration_is_using_current_configuration,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigureCli:
    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        self.app_name = self.cli_configuration.app_name

        env_config_dir = f"{self.app_name}_CONFIG_DIR".upper()
        env_data_dir = f"{self.app_name}_DATA_DIR".upper()
        self.mandatory_env_variables = (env_config_dir, env_data_dir)

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(invoke_without_command=True, help="Configures the application.")
        @click.pass_context
        def configure(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @configure.command(help="Initialises the configuration directory")
        @click.pass_context
        def init(ctx):
            self.__print_header(f"Seeding configuration directory for {self.app_name}")

            cli_context: CliContext = ctx.obj

            self.__pre_configure_init_validation(cli_context)

            if not self.__check_env_vars_set(cli_context):
                error_and_exit("Prerequisite checks failed")

            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-configure init hook")
            hooks.pre_configure_init(ctx)

            # Seed the configuration directory
            logger.debug("Initialising configuration directory")
            self.__seed_configuration_dir(cli_context)

            # Create an encryption key
            create_and_save_key(cli_context.get_key_file())

            logger.debug("Running post-configure init hook")
            hooks.post_configure_init(ctx)

            # After initialising the configuration directory, put it under source control
            ConfigurationGitRepository(cli_context).init()

            logger.info("Finished initialising configuration")

        @configure.command(help="Applies the settings from the configuration.")
        @click.option(
            "--message",
            "-m",
            help="Message describing the changes being applied.",
            default="[autocommit] due to `configure apply`",
            type=click.STRING,
        )
        @click.option(
            "--force",
            is_flag=True,
            help="Overwrite existing generated configuration, regardless of modified status",
        )
        @click.pass_context
        def apply(ctx, message, force):
            cli_context: CliContext = ctx.obj

            self.__pre_configure_apply_validation(cli_context, force=force)

            configuration = ConfigurationManager(
                cli_context.get_app_configuration_file()
            )

            hooks = self.cli_configuration.hooks
            logger.debug("Running pre-configure apply hook")
            hooks.pre_configure_apply(ctx)

            # Commit the changes made to the config repo
            ConfigurationGitRepository(cli_context).commit_changes(message)

            logger.debug("Applying configuration")
            self.__generate_configuration_files(configuration, cli_context)

            logger.debug("Running post-configure apply hook")
            hooks.post_configure_apply(ctx)

            # Put the generated config repo under version control
            GeneratedConfigurationGitRepository(cli_context).init()

            logger.info("Finished applying configuration")

        @configure.command(help="Reads a setting from the configuration.")
        @click.argument("setting")
        @click.pass_context
        def get(ctx, setting):
            cli_context: CliContext = ctx.obj

            self.__pre_configure_get_and_set_validation(cli_context)

            configuration = ConfigurationManager(
                cli_context.get_app_configuration_file()
            )
            print(configuration.get(setting))

        @configure.command(help="Saves a setting to the configuration.")
        @click.argument("setting")
        @click.argument("value")
        @click.pass_context
        def set(ctx, setting, value):
            cli_context: CliContext = ctx.obj

            self.__pre_configure_get_and_set_validation(cli_context)

            configuration = ConfigurationManager(
                cli_context.get_app_configuration_file()
            )
            configuration.set(setting, value)
            configuration.save()

        self.commands = {"configure": configure}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __check_env_vars_set(self, cli_context: CliContext):
        logger.info("Checking prerequisites ...")
        result = True

        for env_variable in self.mandatory_env_variables:
            value = os.environ.get(env_variable)
            if value is None:
                logger.error(
                    "Mandatory environment variable is not defined [%s]", env_variable
                )
                result = False

        return result

    def __seed_configuration_dir(self, cli_context: CliContext):
        self.__print_header("Seeding configuration directory ...")

        logger.info("Copying app configuration file ...")
        seed_app_configuration_file = self.cli_configuration.seed_app_configuration_file
        if not seed_app_configuration_file.is_file():
            error_and_exit(
                f"Seed file [{seed_app_configuration_file}] is not valid. Release is corrupt."
            )

        target_app_configuration_file = cli_context.get_app_configuration_file()
        logger.debug(
            "Copying app configuration file to [%s] ...", target_app_configuration_file
        )
        target_app_configuration_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed_app_configuration_file, target_app_configuration_file)

        logger.info("Copying templates ...")
        templates_dir = cli_context.get_templates_dir()
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
        self.__print_header(f"Generating configuration files")
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
                    template_file, target_file, configuration.get_as_dict()
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
            "generated_from_commit": ConfigurationGitRepository(
                cli_context
            ).get_current_commit_hash(),
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

    def __pre_configure_init_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for 'configure init'.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.info(
            "Checking system configuration is valid before 'configure init' ..."
        )

        # Cannot run configure init if the config directory already exists.
        must_have_checks = [confirm_config_dir_not_exists]

        validate(
            cli_context=cli_context, must_have_checks=must_have_checks, force=False
        )

        logger.info("System configuration is valid")

    def __pre_configure_apply_validation(
        self, cli_context: CliContext, force: bool = False
    ):
        """Ensures the system is in a valid state for 'configure apply'.

        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If True, only warns on validation checks. Defaults to False.
        """
        logger.info(
            "Checking system configuration is valid before 'configure apply' ..."
        )

        # If the config dir doesn't exist, we cannot apply
        must_have_checks = [confirm_config_dir_exists]

        should_have_checks = []

        # If the generated configuration directory exists, test it for 'dirtiness'.
        # Otherwise the generated config doesn't exist, so the directories are 'clean'.
        try:
            confirm_generated_config_dir_exists(cli_context)
            # If the generated config is dirty, or not running against current config, warn before overwriting
            should_have_checks = [
                confirm_generated_config_dir_is_not_dirty,
                confirm_generated_configuration_is_using_current_configuration,
            ]
        except Exception:
            pass

        validate(
            cli_context=cli_context,
            must_have_checks=must_have_checks,
            should_have_checks=should_have_checks,
            force=force,
        )

        logger.info("System configuration is valid")

    def __pre_configure_get_and_set_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for 'configure get'.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.info("Checking system configuration is valid before 'configure get' ...")

        # Block if the config dir doesn't exist as there's nothing to get or set
        must_have_checks = [confirm_config_dir_exists]

        validate(
            cli_context=cli_context, must_have_checks=must_have_checks,
        )

        logger.info("System configuration is valid")

    def __print_header(self, title):
        logger.info(
            """============================================================
                          %s
                          ============================================================""",
            title.upper(),
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
            logger.error(
                "Could not generate file from template. The configuration file is likely missing a setting: %s",
                e,
            )
            exit(1)

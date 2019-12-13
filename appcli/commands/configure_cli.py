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
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

# vendor libraries
import click
from jinja2 import Template, StrictUndefined

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
)

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

METADATA_FILE_NAME = "metadata-configure.json"
""" Name of the file holding metadata from running a configure (relative to the generated configuration directory) """

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

        @configure.command(help="Seeds the configuration directory")
        @click.pass_context
        def init(ctx):
            self.__print_header(f"Seeding configuration directory for {self.app_name}")

            cli_context: CliContext = ctx.obj

            if not self.__init_prequisites_met(cli_context):
                logger.error("Prerequisite checks failed")
                sys.exit(1)

            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-configure init hook")
            hooks.pre_configure_init(ctx)

            # Seed the configuration directory
            logger.debug("Seeding configuration directory")
            self.__seed_configuration_dir(cli_context)

            logger.debug("Running post-configure init hook")
            hooks.post_configure_init(ctx)

            logger.info("Finished configure init")

        @configure.command(help="Reads a setting from the configuration.")
        @click.argument("setting")
        @click.pass_context
        def get(ctx, setting):
            cli_context: CliContext = ctx.obj
            configuration = ConfigurationManager(cli_context.app_configuration_file)
            print(configuration.get(setting))

        @configure.command(help="Saves a setting to the configuration.")
        @click.argument("setting")
        @click.argument("value")
        @click.pass_context
        def set(ctx, setting, value):
            cli_context: CliContext = ctx.obj
            configuration = ConfigurationManager(cli_context.app_configuration_file)
            configuration.set(setting, value)
            configuration.save()

        @configure.command(help="Applies the settings from the configuration.")
        @click.option(
            "--force",
            is_flag=True,
            help="Overwrite existing generated configuration, regardless of modified status",
        )
        @click.pass_context
        def apply(ctx, force):
            cli_context: CliContext = ctx.obj
            configuration = ConfigurationManager(cli_context.app_configuration_file)

            # Don't allow apply if generated directory is dirty
            self._block_on_existing_dirty_generated_config(cli_context, force)

            hooks = self.cli_configuration.hooks
            logger.debug("Running pre-configure apply hook")
            hooks.pre_configure_apply(ctx)

            # Commit the changes made to the conf repo
            ConfigurationGitRepository(cli_context).commit_changes()
            self.__generate_configuration_files(configuration, cli_context)

            logger.debug("Running post-configure apply hook")
            hooks.post_configure_apply(ctx)

            logger.info("Finished configure apply")

        self.commands = {"configure": configure}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __init_prequisites_met(self, cli_context: CliContext):
        logger.info("Checking prerequisites ...")
        result = True

        for env_variable in self.mandatory_env_variables:
            value = os.environ.get(env_variable)
            if value is None:
                logger.error(
                    "Mandatory environment variable is not defined [%s]", env_variable
                )
                result = False

        # if the configuration file exists in the config directory, then don't allow init
        if os.path.isfile(cli_context.app_configuration_file):
            logger.error(
                f"Configuration directory already initialised at [{cli_context.configuration_dir}]"
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

        target_app_configuration_file = cli_context.app_configuration_file
        logger.debug(
            "Copying app configuration file to [%s] ...", target_app_configuration_file
        )
        target_app_configuration_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed_app_configuration_file, target_app_configuration_file)

        logger.info("Copying templates ...")
        templates_dir = cli_context.templates_dir
        templates_dir.mkdir(parents=True, exist_ok=True)
        seed_templates_dir = self.cli_configuration.seed_templates_dir
        if not seed_templates_dir.is_dir():
            logger.error(
                "Seed templates directory [%s] is not valid. Release is corrupt.",
                seed_templates_dir,
            )
            sys.exit(1)

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

        # After initialising the configuration directory, put it under source control
        ConfigurationGitRepository(cli_context).init()

    def __generate_configuration_files(
        self, configuration: Configuration, cli_context: CliContext
    ):
        self.__print_header(f"Generating configuration files")
        generated_configuration_dir = cli_context.generated_configuration_dir

        # If the generated configuration directory is not empty, back it up and delete
        if os.listdir(generated_configuration_dir):
            self._backup_and_remove_directory(generated_configuration_dir)

        generated_configuration_dir.mkdir(parents=True, exist_ok=True)

        configuration_record_file = generated_configuration_dir.joinpath(
            METADATA_FILE_NAME
        )
        if os.path.exists(configuration_record_file):
            logger.info("Clearing successful configuration record ...")
            os.remove(configuration_record_file)
            logger.debug(
                f"Configuration record removed from [{configuration_record_file}]"
            )

        for template_file in cli_context.templates_dir.glob("**/*"):
            relative_file = template_file.relative_to(cli_context.templates_dir)
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

        self.__copy_settings_file_to_generated_dir(cli_context)

        logger.info("Saving successful configuration record ...")
        record = {
            "configure": {
                "apply": {
                    "last_run": datetime.utcnow()
                    .replace(tzinfo=timezone.utc)
                    .isoformat()
                }
            }
        }
        configuration_record_file.write_text(
            json.dumps(record, indent=2, sort_keys=True)
        )
        logger.debug("Configuration record written to [%s]", configuration_record_file)

        GeneratedConfigurationGitRepository(cli_context).init()

    def _backup_and_remove_directory(self, source_dir: Path):
        """Backs up a directory to a tar gzipped file with the current datetimestamp,
        and deletes the existing directory
        
        Args:
            source_dir (Path): Path to the directory to backup and delete
        """

        # The datetime is accurate to seconds (microseconds was overkill), and we remove
        # colon (:) because `tar tvf` doesn't like filenames with those in them
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

        # Remove the existing folder
        shutil.rmtree(source_dir, ignore_errors=True)
        logger.info(
            f"Deleted previous generated configuration directory [{source_dir}]"
        )

    def __copy_settings_file_to_generated_dir(self, cli_context: CliContext):
        """Copies the current settings file to the generated directory as a record of what configuration
        was used to generate those files.

        Args:
            cli_context (CliContext): The context of the currently-running cli
        """
        logger.debug(
            "Copying applied settings file to generated configuration directory"
        )
        applied_configuration_file = cli_context.generated_configuration_dir.joinpath(
            cli_context.app_configuration_file.name
        )
        shutil.copy2(cli_context.app_configuration_file, applied_configuration_file)

        logger.debug("Applied settings written to [%s]", applied_configuration_file)

    def _block_on_existing_dirty_generated_config(
        self, cli_context: CliContext, force: bool
    ):
    """Checks if the generated configuration directory exists, and whether it's dirty.
    If it does exist, and is dirty (tracked files only), then this will error and exit.
    Also provides a mechanism to override this behaviour with a force flag.
    
    Args:
        cli_context (CliContext): the current cli context
        force (bool): whether to pass this check forcefully
    """
        repo: GeneratedConfigurationGitRepository = GeneratedConfigurationGitRepository(
            cli_context
        )
        # If the repository exists, and the repository is dirty (not counting untracked files), then
        # error out with a --force override possible
        if repo.repo_exists() and repo.is_dirty(untracked_files=False):
            if not force:
                error_and_exit(
                    f"Generated configuration repository is dirty, cannot apply. Use --force to override."
                )
            logger.info(
                "Dirty generated configuration repository overwritten due to --force flag."
            )

    def __print_header(self, title):
        logger.info(
            """============================================================
                          %s
                          ============================================================""",
            title.upper(),
        )

    def __generate_from_template(
        self, template_file: Path, target_file: Path, configuration: Configuration
    ):
        template = Template(
            template_file.read_text(),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        try:
            output_text = template.render(configuration)
            target_file.write_text(output_text)
        except Exception as e:
            logger.error(
                "Could not generate file from template. The configuration file is likely missing a setting: %s",
                e,
            )
            exit(1)

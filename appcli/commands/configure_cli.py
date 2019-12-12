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
from datetime import datetime, timezone
from pathlib import Path
from typing import List
import git

# vendor libraries
import click
from jinja2 import Template, StrictUndefined

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

METADATA_FILE_NAME = "metadata-configure.json"
""" Name of the file holding metadata from running a configure (relative to the generated configuration directory) """


# ------------------------------------------------------------------------------
# PRIVATE CLASSES
# ------------------------------------------------------------------------------


class ConfigRepo:
    def __init__(self, repo_path: str):
        self.repo: git.Repo = git.Repo.init(repo_path)
        self.actor: git.Actor = git.Actor(f"cli_managed", "")

    def commit_changes(self, message):
        self.repo.index.add(".gitignore")
        self.repo.index.add("*")
        self.repo.index.commit(message, author=self.actor)


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

            # Seed the configuration directory, and put it under source control
            logger.debug("Seeding configuration and initialising version control")
            self.__seed_configuration_dir(cli_context)
            self.__init_conf_source_control(cli_context)

            # Generate the configuration files, and put those under source control
            logger.debug("Generating configuration and initialising version control")
            configuration = ConfigurationManager(cli_context.app_configuration_file)
            self.__generate_configuration_files(configuration, cli_context)
            self.__init_generated_conf_source_control(cli_context)

            logger.debug("Running post-configure init hook")
            hooks.post_configure_init(ctx)

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
        @click.pass_context
        def apply(ctx):
            cli_context: CliContext = ctx.obj
            configuration = ConfigurationManager(cli_context.app_configuration_file)
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-configure apply hook")
            hooks.pre_configure_apply(ctx)
            self.__generate_configuration_files(configuration, cli_context)
            logger.debug("Running post-configure apply hook")
            hooks.post_configure_apply(ctx)

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

        conf_dir = cli_context.configuration_dir
        if Path(conf_dir).exists():
            logger.error(f"Configuration directory already exists at [{conf_dir}]")
            result = False

        return result

    def __seed_configuration_dir(self, cli_context: CliContext):
        self.__print_header("Seeding configuration directory ...")

        logger.info("Copying app configuration file ...")
        seed_app_configuration_file = self.cli_configuration.seed_app_configuration_file
        if not seed_app_configuration_file.is_file():
            logger.error(
                "Seed file [%s] is not valid. Release is corrupt.",
                seed_app_configuration_file,
            )
            sys.exit(1)
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

    def __init_conf_source_control(self, cli_context: CliContext):

        repo_path = cli_context.configuration_dir

        # Write out a .gitignore to ignore .generated/
        ignore_file = open(repo_path.joinpath(".gitignore"), "w+")
        ignore_file.write(".generated/\n")
        ignore_file.close()

        # Initialise the repo and author for commits
        repo: ConfigRepo = ConfigRepo(repo_path)

        # Add appropriate files to the index and make the initial commit
        repo.commit_changes("init")

    def __init_generated_conf_source_control(self, cli_context: CliContext):

        repo_path = cli_context.generated_configuration_dir

        # Write out a .gitignore
        repo_path.joinpath(".gitignore").touch()

        # Initialise the repo and author for commits
        repo: ConfigRepo = ConfigRepo(repo_path)

        # Add appropriate files to the index and make the initial commit
        repo.commit_changes("init")

    def __configure_all_settings(self, config_manager: ConfigurationManager):
        settings_group: ConfigSettingsGroup
        for settings_group in self.cli_configuration.config_cli.settings_groups:
            self.__configure_settings(config_manager, settings_group)

    def __configure_settings(
        self, config_manager: ConfigurationManager, settings_group: ConfigSettingsGroup
    ):
        self.__print_header(f"Configure {settings_group.title} settings")
        self.__print_current_settings(settings_group.settings, config_manager)
        if self.__confirm(f"Modify {settings_group.title} settings?"):
            self.__prompt_and_update_configuration(
                settings_group.settings, config_manager
            )

    def __save_configuration(self, configuration):
        self.__print_header(f"Saving configuration")
        configuration.save()

    def __generate_configuration_files(
        self, configuration: Configuration, cli_context: CliContext
    ):
        self.__print_header(f"Generating configuration files")
        generated_configuration_dir = cli_context.generated_configuration_dir
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

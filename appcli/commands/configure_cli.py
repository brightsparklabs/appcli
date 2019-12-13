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
from appcli.functions import error_and_exit
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


class Repository:
    """Class which encapsulates different git repo actions for configuration repositories
    """

    def __init__(self, repo_path: str, ignores: List[str] = None):
        self.repo_path = repo_path
        self.ignores = ignores
        self.actor: git.Actor = git.Actor(f"cli_managed", "")

    def init(self):
        logger.debug("Initialising repository at [%s]", self.repo_path)

        # Confirm that a repo doesn't already exist at this directory
        self._confirm_git_repo_not_initialised(self.repo_path)

        # git init, and write to the .gitignore file
        repo = git.Repo.init(self.repo_path)
        logger.debug("Repo initialised at [%s]", repo.working_dir)
        if self.ignores:
            ignore_file = open(self.repo_path.joinpath(".gitignore"), "w+")
            for ignore in self.ignores:
                ignore_file.write(f"{ignore}\n")
            ignore_file.close()
            logger.debug("Wrote out .gitignore with ignores: [%s]", self.ignores)
        else:
            self.repo_path.joinpath(".gitignore").touch()
            logger.debug("Touched .gitignore")

        # do the initial commit on the repo
        repo.index.add(".gitignore")
        repo.index.add("*")
        repo.index.commit("Initialising repository", author=self.actor)
        logger.debug("Initialised repository at [%s].", repo.working_dir)

    def commit_changes(self):
        try:
            repo = git.Repo(self.repo_path)
        except:
            error_and_exit(f"No git repo found at [{self.repo_path}]")

        if not repo.is_dirty(untracked_files=True):
            logger.info(
                "No changes found in repository [%s], no commit was made.",
                repo.working_dir,
            )
            return

        repo.index.add(".gitignore")
        repo.index.add("*")
        changed_files = [diff.a_path for diff in repo.index.diff("HEAD")]

        commit_message = (
            input(
                f"Changes to [{changed_files}]. Optional message describing changes: "
            ).strip()
            or "Committing changes."
        )

        commit_message += f"\nChanged files: {changed_files}"
        repo.index.commit(commit_message, author=self.actor)

    def is_dirty(self):
        try:
            repo = git.Repo(self.repo_path)
        except:
            error_and_exit(f"No git repo found at [{self.repo_path}]")

        return repo.is_dirty(untracked_files=True)

    def _confirm_git_repo_not_initialised(self, repo_path: str):
        """Test if a git repo exists at a given directory. Raise an error if it does.
        
        Args:
            repo_path (str): path to the directory to test
        """
        try:
            git.Repo(repo_path)
        except:
            # An error is raised - the repo does not exist, so this function succeeds
            return

        # A repo was found at [repo_path], so error and exit.
        error_and_exit(f"Cannot initialise repo at [{repo_path}], already exists.")


class ConfigurationRepository(Repository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.configuration_dir, [".generated"])


class GeneratedConfigurationRepository(Repository):
    def __init__(self, cli_context: CliContext):
        super().__init__(cli_context.generated_configuration_dir)


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

            # Generate the configuration files, and put those under source control
            logger.debug("Generating configuration and initialising version control")
            configuration = ConfigurationManager(cli_context.app_configuration_file)
            self.__generate_configuration_files(configuration, cli_context)

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
        @click.option("--force", is_flag=True)
        @click.pass_context
        def apply(ctx, force):
            cli_context: CliContext = ctx.obj
            configuration = ConfigurationManager(cli_context.app_configuration_file)

            # Don't allow apply if generated directory is dirty
            self._block_on_dirty_gen_config(cli_context, force)

            hooks = self.cli_configuration.hooks
            logger.debug("Running pre-configure apply hook")
            hooks.pre_configure_apply(ctx)

            # Commit the changes made to the conf repo
            ConfigurationRepository(cli_context).commit_changes()
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
        ConfigurationRepository(cli_context).init()

    def __generate_configuration_files(
        self, configuration: Configuration, cli_context: CliContext
    ):
        self.__print_header(f"Generating configuration files")
        generated_configuration_dir = cli_context.generated_configuration_dir
        shutil.rmtree(generated_configuration_dir, ignore_errors=True)
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

        GeneratedConfigurationRepository(cli_context).init()

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

    def _block_on_dirty_gen_config(self, cli_context: CliContext, force: bool):
        if GeneratedConfigurationRepository(cli_context).is_dirty():
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

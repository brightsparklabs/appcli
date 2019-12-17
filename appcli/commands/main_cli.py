#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The main (top-level) commands available when running the CLI.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import json
import os
import sys

# vendor libraries
import click

# local libraries
from appcli.functions import error_and_exit, get_generated_configuration_metadata_file
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
)
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class MainCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration
        self.orchestrator = configuration.orchestrator

        # ----------------------------------------------------------------------
        # PUBLIC METHODS
        # ----------------------------------------------------------------------

        @click.command(help="Starts the system.")
        @click.option(
            "--force",
            is_flag=True,
            help="Force start even if generated configuration is out of date",
        )
        @click.pass_context
        def start(ctx, force):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(ctx)

            cli_context: CliContext = ctx.obj
            self.__pre_start_configuration_repository_checks(cli_context, force=force)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.orchestrator.start(ctx.obj)

            logger.debug("Running post-start hook")
            hooks.post_start(ctx, result)

            logger.info("Start command finished with code [%i]", result.returncode)
            sys.exit(result.returncode)

        @click.command(help="Stops the system.")
        @click.pass_context
        def stop(ctx):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-stop hook")
            hooks.pre_stop(ctx)

            logger.info("Stopping %s ...", configuration.app_name)
            result = self.orchestrator.stop(ctx.obj)

            logger.debug("Running post-stop hook")
            hooks.post_stop(ctx, result)

            logger.info("Stop command finished with code [%i]", result.returncode)
            sys.exit(result.returncode)

        # expose the cli commands
        self.commands = {
            "start": start,
            "stop": stop,
            "logs": self.orchestrator.get_logs_command(),
        }

        # create additional group if orchestrator has custom commands
        orchestrator_commands = self.orchestrator.get_additional_commands()
        if len(orchestrator_commands) > 0:

            @click.group(help="Orchestrator specific commands")
            @click.pass_context
            def orchestrator(ctx):
                pass

            for command in orchestrator_commands:
                orchestrator.add_command(command)
            self.commands.update({"orchestrator": orchestrator})

    def __pre_start_configuration_repository_checks(
        self, cli_context: CliContext, force: bool = False
    ):
        """Ensures the system is in a valid state for startup.

        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If False, will only warn on error. On True will error and exit on error. Defaults to False.
        """
        logger.info("Checking system configuration is valid ...")

        config_repo = ConfigurationGitRepository(cli_context)
        generated_config_repo = GeneratedConfigurationGitRepository(cli_context)

        errors = []
        if not config_repo.repo_exists():
            errors.append(
                f"Configuration repository does not exist at [{config_repo.repo_path}]. Please run `configure init`."
            )
        if not generated_config_repo.repo_exists():
            errors.append(
                f"Generated configuration repository does not exist at [{generated_config_repo.repo_path}]. Please run `configure apply`."
            )
        if errors:
            error_and_exit("Configuration invalid:\n- " + "\n- ".join(errors))
        logger.info("Configuration directories exist")

        # Check if the configuration directory contains unapplied changes
        logger.debug("Checking for dirty configuration repository ...")
        if config_repo.is_dirty(untracked_files=True):
            errors.append(
                "Configuration contains changes which have not been applied. Please run `configure apply`."
            )

        # Check if the generated configuration repository has manual modifications to tracked files
        logger.debug("Checking for dirty generated configuration repository ...")
        if generated_config_repo.is_dirty(untracked_files=False):
            errors.append(
                f"Generated configuration at [{generated_config_repo.repo_path}] has been manually modified."
            )

        # Check if the generated configuration is against current configuration commit
        logger.debug("Checking generated configuration is up to date ...")
        metadata_file = get_generated_configuration_metadata_file(cli_context)
        if not os.path.isfile(metadata_file):
            errors.append(
                f"Could not find a metadata file at [{metadata_file}]. Please run `configure apply`"
            )
        else:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                logger.debug("Metadata from generated configuration: %s", metadata)

            generated_commit_hash = metadata["generated_from_commit"]
            configuration_commit_hash = config_repo.get_current_commit_hash()
            if generated_commit_hash != configuration_commit_hash:
                logger.debug(
                    "Generated configuration hash [%s] does not match configuration hash [%s]",
                    generated_commit_hash,
                    configuration_commit_hash,
                )
                errors.append(
                    "Generated configuration is out of date. Please run `configure apply`."
                )

        if errors:
            error_messages = "\n- ".join(errors)
            if not force:
                error_and_exit(
                    f"""System configuration is invalid:
- {error_messages}

Use the `--force` flag to ignore these issues.
Otherwise please address the issues and run `start` again."""
                )
            logger.warn(
                "Force flag `--force` applied. Ignoring the following issues:\n- %s",
                error_messages,
            )

        logger.info("System configuration is valid")

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
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.functions import error_and_exit, get_metadata_file_directory
from appcli.models.configuration import Configuration
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    GeneratedConfigurationGitRepository,
)

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

        @click.command(
            help="Starts the system.\n\nOptionally specify CONTAINER to start only specific containers.",
            context_settings=dict(ignore_unknown_options=True),
        )
        @click.option(
            "--force",
            is_flag=True,
            help="Force start by ignoring configuration mis-configurations",
        )
        @click.pass_context
        def start(ctx, force):
            hooks = self.cli_configuration.hooks

            logger.debug("Running pre-start hook")
            hooks.pre_start(ctx)

            cli_context: CliContext = ctx.obj
            self._pre_start_configuration_repository_checks(cli_context, force=force)

            logger.info("Starting %s ...", configuration.app_name)
            result = self.orchestrator.start(ctx.obj)

            logger.debug("Running post-start hook")
            hooks.post_start(ctx, result)

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

    def _pre_start_configuration_repository_checks(
        self, cli_context: CliContext, force: bool = False
    ):
        """Validate configuration repository states
        
        Args:
            cli_context (CliContext): the current cli context
            force (bool, optional): If False, will only warn on error. On True will error and exit on error. Defaults to False.
        """

        config_repo = ConfigurationGitRepository(cli_context)
        generated_config_repo = GeneratedConfigurationGitRepository(cli_context)

        # If either of the configuration repos do not exist, we block start.
        self._confirm_configuration_directories_exist(
            config_repo, generated_config_repo
        )

        errors = []
        # Check if the configuration directory contains unapplied changes
        if config_repo.is_dirty(untracked_files=True):
            errors.append(
                "Configuration contains un-applied changes. Call 'configure apply' to apply these changes."
            )

        # Check if the generated configuration repository has manual modifications to tracked files
        if generated_config_repo.is_dirty(untracked_files=False):
            errors.append(
                f"Generated configuration at [{generated_config_repo.repo_path}] has been manually modified."
            )

        # Check if the generated configuration is against current configuration commit #
        metadata_file = get_metadata_file_directory(cli_context)
        if not os.path.isfile(metadata_file):
            errors.append(f"Could not find a metadata file at [{metadata_file}]")
        else:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            generated_conf_metadata_commit_hash = metadata["configure"]["apply"][
                "commit_hash"
            ]
            configuration_commit_hash = config_repo.get_current_commit_hash()
            if generated_conf_metadata_commit_hash != configuration_commit_hash:
                errors.append(
                    f"Mismatched hashes between applied and current configuration. Configuration hash: [{configuration_commit_hash}], Applied hash: [{generated_conf_metadata_commit_hash}]"
                )

        if errors:
            message = "\n".join(errors)
            if not force:
                error_and_exit(
                    message
                    + "\nOverride these warnings and continue to start by passing the '--force' flag."
                )
            logger.warn(
                "Force flag '--force' applied. Overriding the following issues:\n%s",
                message,
            )

        logger.info("Passed pre-start configuration directory checks")

    def _confirm_configuration_directories_exist(
        self,
        config_repo: ConfigurationGitRepository,
        generated_config_repo: GeneratedConfigurationGitRepository,
    ):
        """Confirm that the configuration and generated configuration directories exist. Error and exit if either doesn't exist.
        
        Args:
            config_repo (ConfigurationGitRepository): the configuration repository to check
            generated_config_repo (GeneratedConfigurationGitRepository): the generated configuration repository to check
        """
        errors = []
        if not config_repo.repo_exists():
            errors.append(
                f"Configuration repository does not exist at [{config_repo.repo_path}]."
            )
        if not generated_config_repo.repo_exists():
            errors.append(
                f"Generated configuration repository does not exist at [{generated_config_repo.repo_path}]. Run 'configure apply' to fill this repository."
            )

        if errors:
            error_and_exit("\n".join(errors))

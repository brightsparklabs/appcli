#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The migrate command available when running the CLI.

Responsible for migrating the application to a newer version.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library

# vendor libraries
import click

# local libraries
from appcli.functions import execute_validation_functions
from appcli.logger import logger
from appcli.models.configuration import Configuration
from appcli.models.cli_context import CliContext
from appcli.git_repositories.git_repositories import (
    ConfigurationGitRepository,
    confirm_config_dir_is_not_dirty,
    confirm_generated_config_dir_is_not_dirty,
    confirm_generated_configuration_is_using_current_configuration,
)

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class MigrateCli:

    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        @click.command(
            help="Migrates the application configuration to work with the current application version."
        )
        @click.pass_context
        def migrate(ctx):

            cli_context: CliContext = ctx.obj

            self.__pre_migrate_validation(cli_context)

            config_version: str = self._get_config_version(cli_context)
            app_version: str = self._get_app_version(cli_context)

            logger.info(
                f"Migrating configuration at version [{config_version}] to match application version [{app_version}]"
            )

            # If the configuration version matches the application version, no migration is required.
            if config_version == app_version:
                logger.info("Migration not required.")
                return

            # TODO: Should we have a prompt to confirm that the user definitely wants to migrate from X version to Y version? Include a '-y' or '--yes' option to skip the prompt.

            self._migrate_configuration(cli_context)

            logger.info(
                f"Migration successfully completed. Migrated configuration from version [{config_version}] to [{app_version}]"
            )

        # expose the cli command
        self.commands = {"migrate": migrate}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __pre_migrate_validation(self, cli_context: CliContext):
        """Ensures the system is in a valid state for migration.

        Args:
            cli_context (CliContext): the current cli context
        """
        logger.info("Checking system configuration is valid before migration ...")

        execute_validation_functions(
            cli_context=cli_context,
            must_succeed_checks=[confirm_config_dir_is_not_dirty],
            should_succeed_checks=[
                confirm_generated_config_dir_is_not_dirty,
                confirm_generated_configuration_is_using_current_configuration,
            ],
        )

        logger.info("System configuration is valid for migration.")

    def _get_app_version(self, cli_context: CliContext) -> str:
        """Get the target application version, which is the version of the application
        which is currently running in the Docker container.

        Returns:
            str: version of the application according to the Docker container this script is running in.
        """
        return cli_context.app_version

    def _get_config_version(self, cli_context: CliContext) -> str:
        """Get the current configuration repository's version

        Returns:
            str: version of the configuration repository
        """
        # TODO: return the branch name of the configuration repository
        config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            cli_context
        )
        return config_repo.get_current_branch_name()

    def _is_ready_to_migrate(self, cli_context: CliContext) -> bool:
        """Check if the application is in a state where it is ready to migrate cleanly

        Returns:
            bool: returns True if the application is ready for migration, otherwise False.
        """
        try:
            confirm_config_dir_is_not_dirty(cli_context)
        except Exception:
            logger.error(
                "Un-applied changes to configuration repository, so migration cannot continue. Please run 'configure apply'."
            )
            return False

        return True

    def _migrate_configuration(self, cli_context: CliContext):
        """Migrates the configuration version to the current application version
        """

        config_repo: ConfigurationGitRepository = ConfigurationGitRepository(
            cli_context
        )
        app_version = self._get_app_version(cli_context)

        if config_repo.does_branch_exist(app_version):
            # If the branch already exists, then this version has previously been installed.

            # TODO: Handle the case where it was previously installed, but we want multiple versions of a single version. e.g. v1-a, v1-b, v1-c
            logger.warn(
                f"Version [{app_version}] of this application was previously installed. Rolling back to previous configuration. Manual remediation may be required."
            )

            # Change to that branch, no further migration steps will be taken.
            config_repo.checkout_existing_branch(app_version)

        # TODO: read the current configuration
        # TODO: delegate the 'migration' of configuration to the application being upgraded, which returns a migrated config (e.g. 'v2 migrated')

        # Change branch to the clean 'master' branch
        config_repo.checkout_master_branch()

        # TODO: Copy over new version configuration files (re-seed)

        # Create new branch, named after the version being deployed
        config_repo.checkout_new_branch(app_version)

        # Commit the default v2 configuration
        config_repo.commit_changes(
            f"Initialised application at version [{app_version}]"
        )

        # TODO: Compare new v2 config to the 'clean v2', and make sure all settings are there.

        # TODO: Write out 'v2 migrated' variables file

        # Commit the new variables file
        config_repo.commit_changes(
            f"Migrated variables file to version [{app_version}]"
        )

        # >> Now at v2 variables file. Still templates to go.

        # TODO: Diff all non-variables files (i.e. all templates files + w/e else) -> List of changed files, and their changes.

        # TODO: For each changed file, notify user that manual changes will need to be made to that template file. Provide diff.

        # TODO: Once all templates have been upgraded to v2, commit and done with migration!

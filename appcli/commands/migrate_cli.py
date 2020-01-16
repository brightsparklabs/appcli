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
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.configuration import Configuration

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

            config_version: str = self._get_config_version()
            app_version: str = self._get_app_version()

            logger.info(
                f"Migrating configuration at version [{config_version}] to match application version [{app_version}]"
            )

            # If the configuration version matches the application version, no migration is required.
            if config_version == app_version:
                logger.info("Migration not required.")
                return

            # Check if the system is ready to migrate
            if not self._is_ready_to_migrate():
                error_and_exit("Not ready for migration. See errors above.")

            # TODO: Should we have a prompt to confirm that the user definitely wants to migrate from X version to Y version? Include a '-y' or '--yes' option to skip the prompt.

            self._migrate_configuration_to_version(app_version)

            logger.info(
                f"Migration successfully completed. Migrated configuration from version [{config_version}] to [{app_version}]"
            )

        # expose the cli command
        self.commands = {"migrate": migrate}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def _get_app_version(self) -> str:
        """Get the target application version, which is the version of the application
        which is currently running in the Docker container.

        Returns:
            str: version of the application according to the Docker container this script is running in.
        """
        # TODO: return the version of the application from environment variable
        return ""

    def _get_config_version(self) -> str:
        """Get the current configuration repository's version

        Returns:
            str: version of the configuration repository
        """
        # TODO: return the branch name of the configuration repository
        return ""

    def _is_ready_to_migrate(self) -> bool:
        """Check if the application is in a state where it is ready to migrate cleanly

        Returns:
            bool: returns True if the application is ready for migration, otherwise False.
        """
        # TODO: Implement check

        # If the configuration directory is dirty, warn and return False.

        # return True
        return False

    def _migrate_configuration_to_version(self, version: str):
        """Migrates the configuration to another version

        Args:
            version (str): the version to migrate to
        """
        # TODO: Implement

        # Change branch to the clean 'master' branch

        # Copy over new version configuration files (re-seed)

        # Create new branch, named after the version being deployed

        # Commit 'inital' v2

        # >> Now at v2

        # Get variables file at v1 and v1.c

        # Parse and diff these as dictionaries -> List of different key values

        # Parse v2 variables file
        # For each different key value from v1 to v1.c:
        #   If key exists in v2 variables file, then set
        #   If key does not exist in v2 variables file, collect for manual fixing
        # Write out new file and commit

        # Provde user with list of manual fixes required to variables file

        # Commit after applying manual fixes to variables file

        # Diff all non-variables files (i.e. all templates files + w/e else) -> List of changed files, and their changes.

        # For each changed file, notify user that manual changes will need to be made to that template file. Provide diff.

        # Once all templates have been upgraded to v2, commit and done with migration!

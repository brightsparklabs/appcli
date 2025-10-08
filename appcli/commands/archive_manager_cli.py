#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Commands for archiving and rotation of logs and files.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""


# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

# Vendor imports.
import click

# Local imports.
from appcli.stack_manager.archive_manager import ArchiveManager
from appcli.commands.appcli_command import AppcliCommand
from appcli.configuration_manager import ConfigurationManager
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

# The name of the key for the archive block in the stack settings file.
ARCHIVE = "archive"


# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ArchiveManagerCli:
    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        # ------------------------------------------------------------------------------
        # PUBLIC METHODS
        # ------------------------------------------------------------------------------

        @click.command(
            help="Run an archiving ruleset against the data/conf/backups. "
            "Use RULE_NAME to specify the ruleset. "
            "Not specifying a ruleset means they are all executed. "
        )
        @click.option(
            "--pre-stop-services/--no-pre-stop-services",
            default=True,
            is_flag=True,
            help="Whether to stop services BEFORE the archive is executed. Defaults to stop services.",
        )
        @click.option(
            "--post-start-services/--no-post-start-services",
            default=True,
            is_flag=True,
            help="Whether to start services AFTER the archive is complete. Default to start services.",
        )
        @click.argument("rule_name", type=click.STRING, required=False)
        @click.pass_context
        def archive(
            ctx, pre_stop_services: bool, post_start_services: bool, rule_name: str
        ):
            cli_context: CliContext = ctx.obj

            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.ARCHIVE
            )

            try:
                services_cli = cli_context.commands["service"]
            except KeyError:
                # The `service` command is not available, which means the orchestrator has no services to manage.
                # Therefore there are no services to stop.
                logger.info("No services to stop.")
                services_cli = None
                pre_stop_services = False
                post_start_services = False

            if pre_stop_services:
                logger.info("Stopping application services ...")
                try:
                    ctx.invoke(services_cli.commands["shutdown"])
                except SystemExit:
                    # At completion, the invoked command tries to exit the script, so we have to catch
                    # the SystemExit.
                    pass

            archive_manager: ArchiveManager = self.__create_archive_manager(ctx.obj)
            if rule_name is None:
                # Run all archiving rules.
                archive_manager.run_all_archive_rulesets()
            else:
                # Run single archive rule.
                archive_manager.run_archive_ruleset(rule_name)

            if post_start_services:
                logger.info("Starting application services ...")
                try:
                    ctx.invoke(services_cli.commands["start"])
                except SystemExit:
                    # At completion, the invoked command tries to exit the script, so we have to catch
                    # the SystemExit.
                    pass

            if pre_stop_services and not post_start_services:
                logger.warn(
                    "Services have been shutdown by the backup command and were intentionally not restarted."
                )

        # Expose the commands.
        self.commands = {
            "archive": archive,
        }

    def __create_archive_manager(self, cli_context: CliContext) -> ArchiveManager:
        """
        Create a ArchiveManager object from the `archive` section of the stack settings configuration file.

        Returns:
            A ArchiveManager object that contains archive configuration.
        """
        # Get the settings from the `stack-settings` file.
        configuration = ConfigurationManager(cli_context, self.cli_configuration)
        try:
            stack_variables = configuration.get_stack_variable(ARCHIVE)
        except (KeyError, TypeError) as e:
            error_and_exit(f"No archive key found in stack settings. [{e}]")

        if stack_variables is None:
            error_and_exit("Archive key in stack settings was empty.")

        # Create our ArchiveManager from the settings.
        return ArchiveManager(cli_context, stack_variables)

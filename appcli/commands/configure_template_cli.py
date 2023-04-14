#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configures the system templates.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import difflib
import filecmp
import glob
import os
import shutil
from pathlib import Path

# vendor libraries
import click

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class ConfigureTemplateCli:
    def __init__(self, configuration: Configuration):
        self.cli_configuration: Configuration = configuration

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(
            invoke_without_command=True, help="Configures the baseline templates."
        )
        @click.pass_context
        def template(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @template.command(help="Lists all baseline templates.")
        @click.pass_context
        def ls(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_TEMPLATE_LS
            )
            baseline_templates_dir = self.cli_configuration.baseline_templates_dir

            # Get the relative path of all files within the seed templates directory
            files = get_relative_paths_of_all_files_in_directory(baseline_templates_dir)

            for file in files:
                print(file)

        @template.command(help="Gets a baseline template and prints its contents.")
        @click.argument("template")
        @click.pass_context
        def get(ctx, template):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_TEMPLATE_GET
            )
            baseline_templates_dir = self.cli_configuration.baseline_templates_dir

            template_file_path = Path(os.path.join(baseline_templates_dir, template))
            if not template_file_path.exists():
                error_and_exit(f"Could not find template [{template}]")

            print(template_file_path.read_text())

        @template.command(help="Copies a baseline template to the overrides folder.")
        @click.argument("template")
        @click.option(
            "--force",
            is_flag=True,
            help="Overwrite existing override template.",
        )
        @click.pass_context
        def override(ctx, template, force):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_TEMPLATE_OVERRIDE, force
            )
            baseline_templates_dir = self.cli_configuration.baseline_templates_dir

            template_file_path = Path(os.path.join(baseline_templates_dir, template))
            if not template_file_path.exists():
                error_and_exit(f"Could not find template [{template}]")

            override_file_path = (
                cli_context.get_baseline_template_overrides_dir().joinpath(template)
            )

            if override_file_path.exists():
                if not force:
                    error_and_exit(
                        f"Override template already exists at [{override_file_path}]. Use --force to overwrite."
                    )
                logger.info("Force flag provided. Overwriting existing override file.")

            # Makes the override and sub folders if they do not exist
            os.makedirs(override_file_path.parent, exist_ok=True)
            shutil.copy2(template_file_path, override_file_path)
            logger.info(f"Copied template [{template}] to [{override_file_path}]")

        @template.command(help="Diffs overridde templates with the baseline templates.")
        @click.pass_context
        def diff(ctx):
            cli_context: CliContext = ctx.obj
            cli_context.get_configuration_dir_state().verify_command_allowed(
                AppcliCommand.CONFIGURE_TEMPLATE_DIFF
            )
            baseline_templates_dir = self.cli_configuration.baseline_templates_dir
            override_templates_dir = cli_context.get_baseline_template_overrides_dir()

            template_files_rel_paths = get_relative_paths_of_all_files_in_directory(
                baseline_templates_dir
            )

            override_files_rel_paths = get_relative_paths_of_all_files_in_directory(
                override_templates_dir
            )

            not_overriding_overrides = [
                f for f in override_files_rel_paths if f not in template_files_rel_paths
            ]

            if not_overriding_overrides:
                error_message = (
                    "Overrides present with no matching baseline template:\n - "
                )
                error_message += "\n - ".join(not_overriding_overrides)
                logger.warning(error_message)

            overridden_templates = [
                f for f in template_files_rel_paths if f in override_files_rel_paths
            ]

            no_effect_overrides = [
                f
                for f in overridden_templates
                if is_files_matching(f, baseline_templates_dir, override_templates_dir)
            ]

            if no_effect_overrides:
                error_message = "Overrides present which match baseline template:\n - "
                error_message += "\n - ".join(no_effect_overrides)
                logger.warning(error_message)

            effective_overrides = [
                f for f in overridden_templates if f not in no_effect_overrides
            ]

            if effective_overrides:
                logger.info("The following files differ from baseline templates:")
                for template_rel_path in effective_overrides:
                    seed_template = baseline_templates_dir.joinpath(template_rel_path)
                    override_template = override_templates_dir.joinpath(
                        template_rel_path
                    )
                    template_text = open(seed_template).readlines()
                    override_text = open(override_template).readlines()
                    for line in difflib.unified_diff(
                        template_text,
                        override_text,
                        fromfile=f"template - {template_rel_path}",
                        tofile=f"override - {template_rel_path}",
                        lineterm="",
                    ):
                        # remove superfluous \n characters added by unified_diff
                        print(line.rstrip())

        # Expose the commands
        self.command = template

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------


def get_relative_paths_of_all_files_in_directory(directory: Path):
    return [
        os.path.relpath(f, directory)
        for f in glob.glob(str(directory.joinpath("**/*")), recursive=True)
        if os.path.isfile(f)
    ]


def is_files_matching(file_rel_path: str, directory_1: Path, directory_2: Path):
    file_1 = directory_1.joinpath(file_rel_path)
    file_2 = directory_2.joinpath(file_rel_path)
    return filecmp.cmp(file_1, file_2)

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

        self.app_name = self.cli_configuration.app_name

        env_config_dir = f"{self.app_name}_CONFIG_DIR".upper()
        env_data_dir = f"{self.app_name}_DATA_DIR".upper()
        self.mandatory_env_variables = (env_config_dir, env_data_dir)

        # ------------------------------------------------------------------------------
        # CLI METHODS
        # ------------------------------------------------------------------------------

        @click.group(
            invoke_without_command=True, help="Configures the application templates."
        )
        @click.pass_context
        def template(ctx):
            if ctx.invoked_subcommand is not None:
                # subcommand provided
                return

            click.echo(ctx.get_help())

        @template.command(help="Lists all default templates")
        @click.pass_context
        def ls(ctx):
            seed_templates_dir = self.cli_configuration.seed_templates_dir

            # Get the relative path of all files within the seed templates directory
            files = get_relative_paths_of_all_files_in_directory(seed_templates_dir)

            for file in files:
                print(file)

        @template.command(help="Gets a default template and prints its contents.")
        @click.argument("template_rel_path")
        @click.pass_context
        def get(ctx, template_rel_path):
            seed_templates_dir = self.cli_configuration.seed_templates_dir

            template_file_path = Path(
                os.path.join(seed_templates_dir, template_rel_path)
            )
            if not template_file_path.exists():
                error_and_exit(f"Could not find template [{template_rel_path}]")

            print(template_file_path.read_text())

        @template.command(help="Copies a default template to the overrides folder.")
        @click.argument("template_rel_path")
        @click.option(
            "--force", is_flag=True, help="Overwrite existing override template",
        )
        @click.pass_context
        def override(ctx, template_rel_path, force):
            cli_context: CliContext = ctx.obj
            seed_templates_dir = self.cli_configuration.seed_templates_dir

            template_file_path = Path(
                os.path.join(seed_templates_dir, template_rel_path)
            )
            if not template_file_path.exists():
                error_and_exit(f"Could not find template [{template_rel_path}]")

            override_file_path = cli_context.get_template_overrides_dir().joinpath(
                template_rel_path
            )

            if override_file_path.exists():
                if not force:
                    error_and_exit(
                        f"Override template already exists at [{override_file_path}]. Use --force to overwrite."
                    )
                logger.info("Force flag provided. Overwriting existing override file.")

            os.makedirs(override_file_path.parent, exist_ok=True)
            shutil.copy2(template_file_path, override_file_path)
            logger.info(
                f"Copied template [{template_rel_path}] to [{override_file_path}]"
            )

        @template.command(help="Diffs overridde templates with the default templates")
        @click.pass_context
        def diff(ctx):
            cli_context: CliContext = ctx.obj
            seed_templates_dir = self.cli_configuration.seed_templates_dir
            override_templates_dir = cli_context.get_template_overrides_dir()

            template_files_rel_paths = get_relative_paths_of_all_files_in_directory(
                seed_templates_dir
            )

            override_files_rel_paths = get_relative_paths_of_all_files_in_directory(
                override_templates_dir
            )

            not_overriding_overrides = [
                f for f in override_files_rel_paths if f not in template_files_rel_paths
            ]

            overridden_templates = [
                f for f in template_files_rel_paths if f in override_files_rel_paths
            ]

            if not_overriding_overrides:
                error_message = (
                    f"Overrides present with no matching default template:\n - "
                )
                error_message += "\n - ".join(not_overriding_overrides)
                logger.warn(error_message)

            no_effect_overrides = [
                f
                for f in overridden_templates
                if is_files_matching(f, seed_templates_dir, override_templates_dir)
            ]

            effective_overrides = [
                f for f in overridden_templates if f not in no_effect_overrides
            ]

            if no_effect_overrides:
                error_message = f"Overrides present which match default template:\n - "
                error_message += "\n - ".join(no_effect_overrides)
                logger.warn(error_message)

            if effective_overrides:
                for template_rel_path in effective_overrides:
                    seed_template = seed_templates_dir.joinpath(template_rel_path)
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

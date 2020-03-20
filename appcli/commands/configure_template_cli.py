#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configures the system templates.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import glob
import os
from pathlib import Path
import shutil

# vendor libraries
import click

# local libraries
from appcli.functions import error_and_exit
from appcli.logger import logger
from appcli.models.configuration import Configuration
from appcli.models.cli_context import CliContext

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
            files = [
                os.path.relpath(f, seed_templates_dir)
                for f in glob.glob(
                    str(seed_templates_dir.joinpath("**/*")), recursive=True
                )
                if os.path.isfile(f)
            ]

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
        @click.pass_context
        def override(ctx, template_rel_path):
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

            os.makedirs(override_file_path.parent, exist_ok=True)
            shutil.copy2(template_file_path, override_file_path)
            logger.info(
                f"Copied template [{template_rel_path}] to [{override_file_path}]"
            )

        @template.command(help="Diffs overridde templates with the default templates")
        @click.pass_context
        def diff(ctx):
            # cli_context: CliContext = ctx.obj
            # TODO: Impl
            logger.error(f"diff called")

        # Expose the commands
        self.command = template

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------


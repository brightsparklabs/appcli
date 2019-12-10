#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The install command available when running the CLI.

Responsible for installing the application to the host system.

NOTE: This script makes hard assumptions about the location of files. It MUST
      be run within a container.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import os
import sys

# vendor libraries
import click
from jinja2 import Template

# local libraries
from appcli.logger import logger
from appcli.models import Configuration

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class InstallCli:

    # ------------------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        # get the app name
        self.app_name = configuration.app_name

        # environment variables which must be defined
        env_root_dir = f"{self.app_name}_EXT_{self.app_name}_ROOT_DIR".upper()
        self.mandatory_env_variables = [
            "APP_VERSION",
            env_root_dir,
        ]

        # directory containing all app installations
        self.app_root_dir = os.environ.get(env_root_dir)

        # app version
        self.app_version = os.environ.get("APP_VERSION")

        # directory to install this version into
        self.app_home = f"{self.app_root_dir}/{self.app_version}"

        # NOTE: Hide the cli command as end users should not run it manually
        @click.command(hidden=True, help="Installs the system")
        @click.option("--overwrite", is_flag=True)
        def install(overwrite):
            self.__install(overwrite)

        # expose the cli command
        self.commands = {"install": install}

    # ------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------------------

    def __install(self, overwrite):
        logger.info(f"Installing application [v{self.app_version}] ...")
        self.__check_prequisites(overwrite)
        self.__setup_application_home(overwrite)

    def __check_prequisites(self, overwrite_install_dir):
        logger.info("Checking prerequisites ...")
        prerequisites_met = True

        # Check all mandatory environment variables are set
        for env_variable in self.mandatory_env_variables:
            value = os.environ.get(env_variable)
            if value == None:
                logger.error(
                    "Mandatory environment variable is not defined [%s]", env_variable
                )
                prerequisites_met = False

        # Check if the application home already exists and we don't want to overwrite
        if os.path.exists(self.app_home) and not overwrite_install_dir:
            logger.error("Install directory [%s] already exists", self.app_home)
            prerequisites_met = False

        if not prerequisites_met:
            logger.error("Prerequisite checks failed")
            sys.exit(1)

    def __setup_application_home(self, overwrite_install_dir):
        logger.info(f"Setting up [{self.app_home}] ...")
        if os.path.exists(self.app_home) and overwrite_install_dir:
            logger.info("Overwriting extant installation ...")
        else:
            # make the application home folder, and shift the 'current' and 'previous' symlinks
            os.makedirs(self.app_home)
            current_symlink = f"{self.app_root_dir}/current"
            if os.path.exists(current_symlink) or os.path.islink(current_symlink):
                logger.info("Updating [previous] symlink ...")
                previous_symlink = f"{self.app_root_dir}/previous"
                os.replace(current_symlink, previous_symlink)
            logger.info("Updating [current] symlink ...")
            os.symlink(os.path.basename(self.app_home), current_symlink)

        # create launcher
        launcher_file = f"{self.app_home}/{self.app_name}"
        logger.info(f"Creating launcher [{launcher_file}] ...")
        template_file = f"{self.BASE_DIR}/templates/launcher.j2"
        with open(template_file) as f:
            template = Template(f.read())
        template_params = {"app_version": self.app_version, "app_name": self.app_name}
        output_text = template.render(template_params)
        with open(launcher_file, "w") as f:
            f.write(output_text)
        os.chmod(launcher_file, 0o775)

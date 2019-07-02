#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Library for building CLI applications in the brightSPARK Lab style.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import logging
import os
import subprocess
import sys
from typing import NamedTuple

# vendor libraries
import click
import coloredlogs

# ------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------

FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logger = logging.getLogger(__name__)
coloredlogs.install(logger=logger, fmt=FORMAT)

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# directory containing this script
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------

class Configuration(NamedTuple):
    app_name: str
    mandatory_environment_variables: list
    app_root_dir: str
    host_root_dir: str = "/"

class AppCli:
    """Base class for a CLI application"""

    def __init__(self, configuration: Configuration):
        logger.info(f'With mandatory: {configuration.mandatory_environment_variables}')

    @click.group()
    def cli():
        logger.info(f'Running CLI')
        pass

    @cli.command(help="test")
    def test():
        pass

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
The main (top-level) commands available when running the CLI.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import os
import subprocess
import sys
from typing import NamedTuple

# vendor libraries
import click

# internal libraries
from .logger import logger
from .models import Configuration

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------

class MainCli:

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------

    def __init__(self, configuration: Configuration):
        docker_compose_file = configuration.docker_compose_file
        docker_compose_command = [
            'docker-compose',
            '--project-name', configuration.app_name,
            '--file', docker_compose_file
        ]

        @click.command(help='Starts the system')
        @click.pass_context
        def start(ctx):
            logger.info(f'Starting {configuration.app_name} ...')
            command = docker_compose_command + ['up', '-d']
            logger.debug(f'Running [{command}]')
            result = subprocess.run(command)

        @click.command(help='Stops the system')
        @click.pass_context
        def stop(ctx):
            logger.info(f'Stopping {configuration.app_name} ...')
            command = docker_compose_command + ['down']
            logger.debug(f'Running [{command}]')
            result = subprocess.run(command)

        # expose the cli commands
        self.commands = [start, stop]

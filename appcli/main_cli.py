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
        docker_compose_command = [
            'docker-compose',
            '--project-name', configuration.app_name,
            '--file'
        ]

        @click.command(help='Starts the system',
                       context_settings=dict(ignore_unknown_options=True))
        @click.pass_context
        @click.argument('args', nargs=-1, type=click.UNPROCESSED)
        def start(ctx, args):
            logger.info(f'Starting {configuration.app_name} ...')
            __run_and_exit(ctx, ('up', '-d') + args)

        @click.command(help='Stops the system')
        @click.pass_context
        def stop(ctx):
            logger.info(f'Stopping {configuration.app_name} ...')
            __run_and_exit(ctx, ['down'])

        @click.command(help='Streams the system logs',
                       context_settings=dict(ignore_unknown_options=True))
        @click.pass_context
        @click.argument('args', nargs=-1, type=click.UNPROCESSED)
        def logs(ctx, args):
            __run_and_exit(ctx, ('logs', '-f') + args)

        def __get_compose_file_path(ctx):
            return str(ctx.obj['configuration_dir'].joinpath('.generated/conf/cli/docker-compose.yml'))

        def __run_and_exit(ctx, subcommand):
            command = docker_compose_command + [__get_compose_file_path(ctx)]
            command.extend(subcommand)
            logger.debug(f'Running [{" ".join(command)}]')
            result = subprocess.run(command)
            sys.exit(result.returncode)

        # expose the cli commands
        self.commands = [start, stop, logs]

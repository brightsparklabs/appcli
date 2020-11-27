#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Strategies for allowing appcli commands based on configuration and generated
directory states.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries

# vendor libraries

# local libraries
# from appcli.logger import logger

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


from typing import Iterable


class ConfigurationStrategy:
    def __init__(self, cannot_run, cannot_run_unless_forced) -> None:
        self.cannot_run = cannot_run
        self.cannot_run_unless_forced = cannot_run_unless_forced

    def is_command_allowed(self, command: Iterable[str], force: bool):
        temp_command = None
        for token in command:
            if temp_command is None:
                temp_command = token
            else:
                temp_command = " ".join([temp_command, token])

            if temp_command in self.cannot_run:
                # logger.error(self.cannot_run[temp_command])
                print(self.cannot_run[temp_command])
                return False
            if temp_command in self.cannot_run_unless_forced and not force:
                # logger.error(self.cannot_run_unless_forced[temp_command])
                print(self.cannot_run_unless_forced[temp_command])
                return False
        return True


class ConfigurationStrategyFactory:
    def get_strategy() -> ConfigurationStrategy:
        # TODO: Impl. Determine what it needs passed in.
        return CleanConfigurationStrategy()


class CleanConfigurationStrategy(ConfigurationStrategy):
    """Represents the strategy where config and generated directories both exist
    and are in a clean state.
    """

    def __init__(self) -> None:

        cannot_run = {"configure init": "Cannot initialise, already exists."}
        cannot_run_unless_forced = {}

        super().__init__(cannot_run, cannot_run_unless_forced)

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Factory class for getting remote backup strategies.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from datetime import datetime
from pathlib import Path

# local libraries
from appcli.backup_manager.remote_strategy import RemoteBackupStrategy, AwsS3Strategy
from appcli.logger import logger

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------
TYPE = "type"
STRATEGIES = {"S3": AwsS3Strategy}


class RemoteStrategyFactory:
    """
    Factory for getting all remote strategies that match the config
    """

    @staticmethod
    def get_strategy(remote_type, configuration) -> RemoteBackupStrategy:

        # Get the strategy class for the specified type.
        strategy_class = STRATEGIES.get(remote_type, None)

        if strategy_class is None:
            raise TypeError(f"No remote backup strategies found for type {backup['type']}")

        # Instantiate the strategy class and return that instance.
        return strategy_class.from_dict(configuration)

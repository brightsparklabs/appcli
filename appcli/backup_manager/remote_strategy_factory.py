#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Factory class for getting remote backup strategies.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# local libraries
from appcli.backup_manager.remote_strategy import AwsS3Strategy, RemoteBackupStrategy

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------
STRATEGIES = {"S3": AwsS3Strategy}
""" A dict of remote strategy classes that are implemented. """


class RemoteStrategyFactory:
    """
    Factory for getting all remote strategies that match the config
    """

    @staticmethod
    def get_strategy(remote_type: str, configuration: dict) -> RemoteBackupStrategy:
        """
        Get an instance of a remote strategy for a given remote strategy type.

        Args:
            remote_type: (str). The type of strategy to build.
            configuration: (dict). The extra configuration values to use in building the strategy.

        Returns:
            An instance of a strategy class.

        """

        # Get the strategy class for the specified type.
        strategy_class = STRATEGIES.get(remote_type, None)

        if strategy_class is None:
            raise TypeError(
                f"No remote backup strategies found for type [{remote_type}]"
            )

        # Instantiate the strategy class and return that instance.
        return strategy_class.from_dict(configuration)

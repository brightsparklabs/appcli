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
from appcli.backup_manager.remote_strategy import AwsS3Strategy
from appcli.logger import logger


class RemoteStrategyFactory:
    """
    Factory for getting all remote strategies that match the config
    """

    @staticmethod
    def get_strategy(backup_manager, key_file: Path):
        strategies = {"S3": AwsS3Strategy}

        backup_strategies = []

        for backup in backup_manager.remote_strategy_config:
            cl = strategies.get(backup["type"], lambda: "Invalid remote strategy")

            if isinstance(cl, str):
                logger.error(
                    f"No remote backup strategies found for type {backup['type']}"
                )

            strategy = cl(backup, key_file)

            if RemoteStrategyFactory.__frequency_check(strategy.frequency):
                backup_strategies.append(strategy)

        return backup_strategies

    def __frequency_check(frequency):
        """
        Check if today matches the pseudo cron `frequency`.
        Frequency format is `* * *`:
        First `*` is the day of the month.
        Second `*` is the month.
        Third `*` is the day of the week starting with monday=0.
        `*` is a wildcard that is always matched.
        e.g.
        `* * *` Will always return True.
        `* * 0` Will only return True on Mondays.

        Args:
            frequency: str. A frequency string that is checked to see if a backup should occur today.
        Returns:
            True if today matches the frequency, False if it does not.
        """
        if not len(frequency) == 5:
            logger.error(f"Frequency string is invalid - {frequency}")
            return False

        toReturn = True

        day_of_month = frequency[0]
        month = frequency[2]
        day_of_week = frequency[4]

        today = datetime.today()

        if day_of_month.isnumeric():
            if not int(day_of_month) == today.day:
                toReturn = False

        if month.isnumeric():
            if not int(month) == today.month:
                toReturn = False

        if day_of_week.isnumeric():
            if not int(day_of_week) == today.weekday():
                toReturn = False

        return toReturn

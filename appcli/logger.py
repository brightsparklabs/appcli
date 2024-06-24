#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Central logger.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import logging

# vendor libraries
import coloredlogs

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# Format for logger messages
LOGGER_FORMAT = "%(asctime)s %(levelname)s: %(message)s"

# Date format for logger messages
LOGGER_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# ------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.propagate = False


def configure_default_logging():
    coloredlogs.install(logger=logger, fmt=LOGGER_FORMAT, datefmt=LOGGER_DATE_FORMAT)


def enable_debug_logging():
    coloredlogs.install(
        logger=logger,
        fmt=LOGGER_FORMAT,
        level=logging.DEBUG,
        datefmt=LOGGER_DATE_FORMAT,
    )
    logger.debug("Enabled debug mode")


def enable_dev_mode_logging():
    logger_format = "DEV_MODE | %(asctime)s %(levelname)s: %(message)s"
    coloredlogs.install(
        logger=logger,
        fmt=logger_format,
        level=logging.DEBUG,
    )


configure_default_logging()

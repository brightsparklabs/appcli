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
# LOGGING
# ------------------------------------------------------------------------------

LOGGER_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
LOGGER_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S %Z"
logger = logging.getLogger(__name__)
logger.propagate = False
coloredlogs.install(logger=logger, fmt=LOGGER_FORMAT, datefmt=LOGGER_DATE_FORMAT)


def enable_debug_logging():
    coloredlogs.install(
        logger=logger,
        fmt=LOGGER_FORMAT,
        level=logging.DEBUG,
        datefmt=LOGGER_DATE_FORMAT,
    )
    logger.debug("Enabled debug mode")

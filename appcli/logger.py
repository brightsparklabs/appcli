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

LOGGER_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logger = logging.getLogger(__name__)
coloredlogs.install(logger=logger, fmt=LOGGER_FORMAT)

def enable_debug_logging():
    coloredlogs.install(logger=logger, fmt=LOGGER_FORMAT, level=logging.DEBUG)
    logger.debug("Enabled debug mode")

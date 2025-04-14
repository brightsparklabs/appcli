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
import base64
import sys
from types import MethodType

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


def _sensitive(self, key: str, value: str | bytes) -> None:
    """Print a sensitive value to stderr in Base-64 encoding.

    Args:
        key: Name of the secret to be printed.
        value: Value of the secret to be printed.
    """
    # Run some checks on the args.
    if not isinstance(key, str):
        raise TypeError(f"Key must be a string, got {type(key)}")
    if isinstance(value, str):
        value_bytes = value.encode("utf-8")
    elif isinstance(value, bytes):
        value_bytes = value
    else:
        raise TypeError(f"Value must be str or bytes, got {type(value)}")

    # Generate the message.
    encoded_value = base64.b64encode(value_bytes).decode("utf-8")
    message = f"{key}: {encoded_value}"

    # Configure the new handler.
    stream = sys.stderr
    formatter = logging.Formatter("[SENSITIVE] %(message)s")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)

    # Emit the log directly through the handler (not via logger).
    record = self.makeRecord(
        name=self.name,
        level=logging.DEBUG,
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    handler.handle(record)


# Attach new logging function.
logger.sensitive = MethodType(_sensitive, logger)


configure_default_logging()

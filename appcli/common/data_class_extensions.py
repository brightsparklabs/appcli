#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Extensions to the DataClass library.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from dataclasses import MISSING, fields

# local libraries
from appcli.logger import logger


class DataClassExtensions:
    """Extensions for the DataClass library."""

    def fix_defaults(self):
        """
        Set the default value for any field that is 'None' or empty.
        Dataclass interprates an empty field as intentionally empty ('None') and will disregard the default,
        we need to check if any field is 'None' but had a valid default and set it.

        The order in which to try to set the value is:
        - f.default if it's defined, otherwise
        - f.default_factory() if f.default_factory is defined, otherwise
        - None (as there's no other reasonable default).
        """
        for f in fields(self):
            val = getattr(self, f.name)
            if val is None or not val:
                default_value = None
                if f.default != MISSING:
                    default_value = f.default
                elif f.default_factory != MISSING:
                    default_value = f.default_factory()

                logger.debug(
                    f"Overriding 'None' for [{f.name}] with default [{default_value}]"
                )
                setattr(self, f.name, default_value)

    def __post_init__(self):
        self.fix_defaults()

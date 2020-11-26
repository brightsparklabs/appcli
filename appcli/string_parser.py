#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Parse strings to other Python types.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
from distutils.util import strtobool
from typing import List

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class StringParser:

    # The 'type' string for string to string parsing (i.e. identity function)
    STRING_PARSER_TYPE = "str"

    # The supported parsing functions
    PARSING_FUNCTIONS = {
        STRING_PARSER_TYPE: lambda s: (s),
        "bool": lambda s: (bool(strtobool(s))),
        "int": lambda s: (int(s)),
        "float": lambda s: (float(s)),
    }

    def get_string_parser_type() -> str:
        """Gets the 'type' string for parsing string to string (i.e. identity function).

        Returns:
            str: The 'type' string representing a string to string parsing.
        """
        return StringParser.STRING_PARSER_TYPE

    def get_types() -> List[str]:
        """Gets the list of supported 'types' for parsing.

        Returns:
            List[str]: List of valid 'types' for parsing.
        """
        return list(StringParser.PARSING_FUNCTIONS.keys())

    def parse(value: str, type: str) -> any:
        """Parse a string to a supported type.

        For example, parse "12345" as an "int" (integer).

        Args:
            value (str): Value to parse.
            type (str): The type of the output value after parsing. Only supports the types returned by StringParser.get_types().

        Raises:
            RuntimeError: Raised if the value cannot be parsed due to invalid 'type' argument.
            Exception: Raised on any other parsing exception.

        Returns:
            [any]: The parsed value as the specified type.
        """
        valid_types: List[str] = StringParser.get_types()
        if type not in valid_types:
            raise RuntimeError(
                f"Cannot parse value [{value}] as type [{type}]. Type must be one of [{valid_types}]."
            )

        try:
            return StringParser.PARSING_FUNCTIONS.get(type)(value)
        except Exception as exception:
            raise Exception(
                f"Error while parsing [{value}] as type [{type}]."
            ) from exception

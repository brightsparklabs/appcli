#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Transforms strings to other Python types.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
from typing import List

# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


# NOTE: This is a copy of the `distutils.util.strtobool` function.
# `distutils` is depricated and removed in python-3.12.
# See https://docs.python.org/3/whatsnew/3.10.html#distutils-deprecated
# And https://github.com/python/cpython/blob/3.10/Lib/distutils/util.py#L308
# And https://stackoverflow.com/questions/42248342/yes-no-prompt-in-python3-using-strtobool
def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class StringTransformer:
    # The 'type' string for string to string transformation (i.e. identity function)
    STRING_TRANSFORMER_TYPE = "str"

    # The supported transformation functions
    TRANSFORMATION_FUNCTIONS = {
        STRING_TRANSFORMER_TYPE: lambda s: (str(s)),
        "bool": lambda s: (bool(strtobool(s))),
        "int": lambda s: (int(s)),
        "float": lambda s: (float(s)),
    }

    def get_string_transformer_type() -> str:
        """Gets the 'type' string for transforming string to string (i.e. identity function).

        Returns:
            str: The 'type' string representing a string to string transformation.
        """
        return StringTransformer.STRING_TRANSFORMER_TYPE

    def get_types() -> List[str]:
        """Gets the list of supported 'types' for transformation.

        Returns:
            List[str]: List of valid 'types' for transformation.
        """
        return list(StringTransformer.TRANSFORMATION_FUNCTIONS.keys())

    def transform(value: str, type: str) -> any:
        """Transform a string to a supported type.

        For example, transform "12345" as an "int", returns the integer value 12345.

        Args:
            value (str): Value to transform.
            type (str): The type of the output value after transformation. Only supports the types returned by StringTransformer.get_types().

        Raises:
            RuntimeError: Raised if the value cannot be transformed due to invalid 'type' argument.
            Exception: Raised on any other transformation exception.

        Returns:
            [any]: The transformed value as the specified type.
        """
        valid_types: List[str] = StringTransformer.get_types()
        if type not in valid_types:
            raise RuntimeError(
                f"Cannot transform value [{value}] as type [{type}]. Type must be one of [{valid_types}]."
            )

        try:
            return StringTransformer.TRANSFORMATION_FUNCTIONS.get(type)(value)
        except Exception as exception:
            raise Exception(
                f"Error while transforming [{value}] as type [{type}]."
            ) from exception

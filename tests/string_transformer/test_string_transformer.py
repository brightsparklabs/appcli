#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for StringTransformer.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import pytest

# local libraries
from appcli.string_transformer import StringTransformer

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_transform_to_string():
    assert transform_string("abc") == "abc"
    assert transform_string(123) == "123"
    assert transform_string({}) == "{}"


def test_transform_to_boolean():
    assert transform_boolean("True") is True
    assert transform_boolean("yes") is True
    assert transform_boolean("Y") is True

    assert transform_boolean("FALSE") is False
    assert transform_boolean("No") is False
    assert transform_boolean("n") is False

    with pytest.raises(Exception):
        # Expect that we cannot transform an empty string to a boolean
        transform_boolean("")

    with pytest.raises(Exception):
        # Expect that we cannot transform a string to a boolean
        transform_boolean("some string value")

    with pytest.raises(Exception):
        # Expect that we cannot transform an integer a boolean
        transform_boolean(0)


def test_transform_to_integer():
    assert transform_integer(123) == 123
    assert transform_integer("123123") == 123123

    with pytest.raises(Exception):
        # Expect that we cannot transform a string to an integer
        transform_integer("some string value")


def test_transform_to_float():
    assert transform_float(123) == 123.0
    assert transform_float("123.456") == 123.456

    with pytest.raises(Exception):
        # Expect that we cannot transform a string to an integer
        transform_float("some string value")


def test_invalid_transform_type():
    with pytest.raises(RuntimeError):
        StringTransformer.transform("value", "invalid_transform")

    with pytest.raises(RuntimeError):
        StringTransformer.transform("value", 123)


# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------


def transform_string(value):
    return StringTransformer.transform(value, "str")


def transform_boolean(value):
    return StringTransformer.transform(value, "bool")


def transform_integer(value):
    return StringTransformer.transform(value, "int")


def transform_float(value):
    return StringTransformer.transform(value, "float")

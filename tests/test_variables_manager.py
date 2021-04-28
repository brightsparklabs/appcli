#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for configuration manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from pathlib import Path
import filecmp
from pyparsing import Dict

# vendor libraries
import pytest
from deepdiff import DeepDiff
from ruamel import yaml

# local libraries
from appcli.variables_manager import VariablesManager

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "test_app"

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------

# TODO: resource file doesnt exist
# TODO: resource file isnt .yml
# TODO: set test cases

# GET


def test_get_variable_before_set(tmpdir):
    """When the path to a variable does not exist we expect a KeyError exception"""
    var_manager = create_var_manager_from_resource("test_app")
    variable_path = "nonexistant.variable"
    with pytest.raises(KeyError) as pytest_wrapped_e:
        var_manager.get_variable(variable_path)
    assert pytest_wrapped_e.type == KeyError


def test_get_variable_empty(tmpdir):
    """When we retrieve a variable with a no value, we expect the return type to be None"""
    var_manager = create_var_manager_from_resource("test_app_empty_value")
    variable_path = "empty"
    assert var_manager.get_variable(variable_path) is None


def test_get_string_variable(tmpdir):
    """When retriving a string it should be equal to the value of an identical string"""
    var_manager = create_var_manager_from_resource("test_app_string_value")
    variable_path = "string"
    test_value = "Value"
    assert var_manager.get_variable(variable_path) == test_value


def test_get_bool_variable(tmpdir):
    """When retriving a boolean it should be equal to the value of an identical boolean"""
    var_manager = create_var_manager_from_resource("test_app_bool_value")
    # test if booleans with value 'False' return as expected
    variable_path = "false_boolean"
    assert not var_manager.get_variable(variable_path)
    # test if booleans with value 'True' return as expected
    variable_path = "true_boolean"
    assert var_manager.get_variable(variable_path)


def test_get_float_variable(tmpdir):
    """When retriving a float it should be equal to the value of an identical float"""
    var_manager = create_var_manager_from_resource("test_app_float_value")
    variable_path = "float"
    test_value = 12345.6789
    assert var_manager.get_variable(variable_path) == test_value


def test_get_int_variable(tmpdir):
    """When retriving a int it should be equal to the value of an identical int"""
    var_manager = create_var_manager_from_resource("test_app_int_value")
    variable_path = "int"
    test_value = 12345
    assert var_manager.get_variable(variable_path) == test_value


def test_get_all_variables(tmpdir):
    """The dictionary returned from get_all_variables() should be equal to the dictionary used to set it"""
    var_manager = create_var_manager_from_resource("test_app_get_all_variables")
    dictionary = {
        "object": {
            "booleans": {
                "false_boolean": False,
                "true_boolean": True,
            },
            "float": 12345.6789,
            "int": 12345,
            "string": "Value",
        },
    }
    assert (
        DeepDiff(
            var_manager.get_all_variables(),
            dictionary,
            ignore_type_in_groups=[
                (yaml.comments.CommentedMap, dict),
                (yaml.scalarfloat.ScalarFloat, float),
            ],
        )
        == {}
    )


# SET


def test_set_variable_empty(tmpdir):
    """When we set a variable with a no value, we expect the variable to have no value in our yml file"""
    set_config_file = Path(tmpdir, "test_app_set_variable_empty.yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file)
    variable_path = "empty"
    var_manager.set_variable(variable_path, None)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_empty_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_string_variable(tmpdir):
    """"""
    set_config_file = Path(tmpdir, "test_app_set_string_variable.yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file)
    variable_path = "string"
    variable_value = "Value"
    var_manager.set_variable(variable_path, variable_value)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_string_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_bool_variable(tmpdir):
    """"""
    set_config_file = Path(tmpdir, "test_app_set_bool_variable.yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file)
    variable_path_false = "false_boolean"
    variable_path_true = "true_boolean"
    var_manager.set_variable(variable_path_false, False)
    var_manager.set_variable(variable_path_true, True)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_bool_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_float_variable(tmpdir):
    """"""
    set_config_file = Path(tmpdir, "test_app_set_float_variable.yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file)
    variable_path = "float"
    variable_value = 12345.6789
    var_manager.set_variable(variable_path, variable_value)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_float_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_int_variable(tmpdir):
    """"""
    set_config_file = Path(tmpdir, "test_app_set_int_variable.yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file)
    variable_path = "int"
    variable_value = 12345
    var_manager.set_variable(variable_path, variable_value)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_int_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_all_variables(tmpdir):
    """The dictionary used to set set_all_variables() should be equal to the dictionary returned from it"""
    set_config_file = Path(tmpdir, "test_app_set_all_variables.yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file)
    dictionary = {
        "object": {
            "booleans": {
                "false_boolean": False,
                "true_boolean": True,
            },
            "float": 12345.6789,
            "int": 12345,
            "string": "Value",
        },
    }
    var_manager.set_all_variables(dictionary)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_get_all_variables.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_var_manager_from_resource(configFile) -> VariablesManager:
    """"""
    # directory containing this script
    return VariablesManager(
        Path(Path(__file__).parent, f"variables_manager_resources/{configFile}.yml")
    )

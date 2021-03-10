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

# vendor libraries
import pytest

# local libraries
from appcli import CliContext, Configuration, DockerComposeOrchestrator
from appcli.variables_manager import VariablesManager

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "test_app"

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_get_variable_before_set(tmpdir):
    var_manager = create_var_manager(tmpdir, "test_app")
    variable_path = "nonexistant.key"
    with pytest.raises(NameError) as pytest_wrapped_e:
        var_manager.get_variable(variable_path)
    assert pytest_wrapped_e.type == NameError


def test_get_variable_empty(tmpdir):
    var_manager = create_var_manager(tmpdir, "test_app_empty_value")
    variable_path = "empty"
    assert var_manager.get_variable(variable_path) == None


def test_get_variable(tmpdir):
    var_manager = create_var_manager(tmpdir, "test_app_string_value")
    variable_path = "string"
    test_value = "Value"
    var_manager.set_variable(variable_path, test_value)
    assert var_manager.get_variable(variable_path) == test_value


def test_get_bool_variable(tmpdir):
    var_manager = create_var_manager(tmpdir, "test_app_bool_value")
    # test if booleans with value 'False' return as expected
    variable_path = "false_boolean"
    assert var_manager.get_variable(variable_path) == False
    # test if booleans with value 'True' return as expected
    variable_path = "true_boolean"
    assert var_manager.get_variable(variable_path) == True


def test_get_float_variable(tmpdir):
    var_manager = create_var_manager(tmpdir, "test_app_float_value")
    variable_path = "float"
    test_value = 12345.6789
    var_manager.set_variable(variable_path, test_value)
    assert var_manager.get_variable(variable_path) == test_value


def test_get_int_variable(tmpdir):
    var_manager = create_var_manager(tmpdir, "test_app_int_value")
    variable_path = "int"
    test_value = 12345
    var_manager.set_variable(variable_path, test_value)
    assert var_manager.get_variable(variable_path) == test_value


def test_get_all_variables(tmpdir):
    # test_app_set_all_variables.yml => dictionary == dictionary
    var_manager = create_var_manager(tmpdir, "test_app_get_all_variables")
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
    assert var_manager.get_all_variables() == dictionary


def test_set_all_variables(tmpdir):
    # dictionary => configuration == test_app_set_all_variables.yml
    var_manager = create_var_manager(tmpdir, "test_app_set_all_variables")
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

    set_file = tmpdir.read("test_app_set_all_variables.yml")
    compare_file = Path(Path(__file__).parent, "variables_manager_resources/test_app_get_all_variables.yml")

    assert filecmp.cmp(set_file, compare_file) == True


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_var_manager(tmpdir, configFile) -> VariablesManager:
    # directory containing this script
    BASE_DIR = Path(__file__).parent
    return VariablesManager(
        Path(BASE_DIR, f"variables_manager_resources/{configFile}.yml")
    )

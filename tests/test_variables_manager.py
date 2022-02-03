#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for configuration manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import filecmp
from pathlib import Path

# vendor libraries
import pytest
from deepdiff import DeepDiff
from ruamel import yaml

# local libraries
from appcli.variables_manager import VariablesManager

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

# Path to the test keyfile for encryption
TEST_KEY_PATH: Path = Path(
    Path(__file__).parent, "variables_manager_resources/test_key"
)

# Directory containing extra configuration files
ADDITIONAL_CONFIG_DIR = "resources/template/appcli/empty"

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_get_variable_before_set(tmpdir):
    """When the path to a variable does not exist we expect a KeyError exception"""
    name_of_test = "test_app"
    var_manager = create_var_manager_from_resource(name_of_test)
    variable_path = name_of_test + ".nonexistant.variable"
    with pytest.raises(KeyError) as pytest_wrapped_e:
        var_manager.get_variable(variable_path)
    assert pytest_wrapped_e.type == KeyError


def test_get_variable_empty(tmpdir):
    """When we retrieve a variable with a no value, we expect the return type to be None"""
    name_of_test = "test_app_empty_value"
    var_manager = create_var_manager_from_resource(name_of_test)
    variable_path = name_of_test + ".empty"
    assert var_manager.get_variable(variable_path) is None


def test_get_string_variable(tmpdir):
    """When retriving a string it should be equal to the value of an identical string"""
    name_of_test = "test_app_string_value"
    var_manager = create_var_manager_from_resource(name_of_test)
    variable_path = name_of_test + ".string"
    test_value = "Value"
    assert var_manager.get_variable(variable_path) == test_value


def test_get_bool_variable(tmpdir):
    """When retriving a boolean it should be equal to the value of an identical boolean"""
    name_of_test = "test_app_bool_value"
    var_manager = create_var_manager_from_resource(name_of_test)
    # test if booleans with value 'False' return as expected
    variable_path = name_of_test + ".false_boolean"
    assert not var_manager.get_variable(variable_path)
    # test if booleans with value 'True' return as expected
    variable_path = name_of_test + ".true_boolean"
    assert var_manager.get_variable(variable_path)


def test_get_float_variable(tmpdir):
    """When retriving a float it should be equal to the value of an identical float"""
    name_of_test = "test_app_float_value"
    var_manager = create_var_manager_from_resource(name_of_test)
    variable_path = name_of_test + ".float"
    test_value = 12345.6789
    assert var_manager.get_variable(variable_path) == test_value


def test_get_int_variable(tmpdir):
    """When retriving a int it should be equal to the value of an identical int"""
    name_of_test = "test_app_int_value"
    var_manager = create_var_manager_from_resource(name_of_test)
    variable_path = name_of_test + ".int"
    test_value = 12345
    assert var_manager.get_variable(variable_path) == test_value


def test_get_all_variables(tmpdir):
    """The dictionary returned from get_all_variables() should be equal to the dictionary used to set it"""
    name_of_test = "test_app_get_all_variables"
    var_manager = create_var_manager_from_resource(name_of_test)
    dictionary = {
        name_of_test: {
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


def test_set_variable_empty(tmpdir):
    """When we set a variable with a no value, we expect the variable to have no value in our yml file"""
    name_of_test = "test_app_set_variable_empty"
    set_config_file = Path(tmpdir, name_of_test + ".yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file, key_file=TEST_KEY_PATH, extra_configuration_files=Path(ADDITIONAL_CONFIG_DIR))
    variable_path = name_of_test + ".empty"
    var_manager.set_variable(variable_path, None)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_empty_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_string_variable(tmpdir):
    """When we set a variable of type string, we expect the varible to be of type string in our yml file"""
    name_of_test = "test_app_set_string_variable"
    set_config_file = Path(tmpdir, name_of_test + ".yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file, key_file=TEST_KEY_PATH, extra_configuration_files=Path(ADDITIONAL_CONFIG_DIR))
    variable_path = name_of_test + ".string"
    variable_value = "Value"
    var_manager.set_variable(variable_path, variable_value)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_string_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_bool_variable(tmpdir):
    """When we set a variable of type bool, we expect the varible to be of type bool in our yml file"""
    name_of_test = "test_app_set_bool_variable"
    set_config_file = Path(tmpdir, name_of_test + ".yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file, key_file=TEST_KEY_PATH, extra_configuration_files=Path(ADDITIONAL_CONFIG_DIR))
    variable_path_false = name_of_test + ".false_boolean"
    variable_path_true = name_of_test + ".true_boolean"
    var_manager.set_variable(variable_path_false, False)
    var_manager.set_variable(variable_path_true, True)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_bool_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_float_variable(tmpdir):
    """When we set a variable of type float, we expect the varible to be of type float in our yml file"""
    name_of_test = "test_app_set_float_variable"
    set_config_file = Path(tmpdir, name_of_test + ".yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file, key_file=TEST_KEY_PATH, extra_configuration_files=Path(ADDITIONAL_CONFIG_DIR))
    variable_path = name_of_test + ".float"
    variable_value = 12345.6789
    var_manager.set_variable(variable_path, variable_value)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_float_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_int_variable(tmpdir):
    """When we set a variable of type int, we expect the varible to be of type int in our yml file"""
    name_of_test = "test_app_set_int_variable"
    set_config_file = Path(tmpdir, name_of_test + ".yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file, key_file=TEST_KEY_PATH, extra_configuration_files=Path(ADDITIONAL_CONFIG_DIR))
    variable_path = name_of_test + ".int"
    variable_value = 12345
    var_manager.set_variable(variable_path, variable_value)
    compare_file = Path(
        Path(__file__).parent,
        "variables_manager_resources/test_app_int_value.yml",
    )
    assert filecmp.cmp(set_config_file, compare_file)


def test_set_all_variables(tmpdir):
    """The dictionary used to set set_all_variables() should be equal to the dictionary returned from it"""
    name_of_test = "test_app_set_all_variables"
    set_config_file = Path(tmpdir, name_of_test + ".yml")
    set_config_file.touch()
    var_manager = VariablesManager(set_config_file, key_file=TEST_KEY_PATH, extra_configuration_files=Path(ADDITIONAL_CONFIG_DIR))
    dictionary = {
        name_of_test: {
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


def create_var_manager_from_resource(config_name) -> VariablesManager:
    """Creates a variables manager object from a file in our variables_manager_resources directory"""
    # directory containing this script
    return VariablesManager(
        Path(Path(__file__).parent, f"variables_manager_resources/{config_name}.yml"),
        key_file=TEST_KEY_PATH,
        extra_configuration_files=Path(Path(__file__).parent, f"{ADDITIONAL_CONFIG_DIR}"),
    )

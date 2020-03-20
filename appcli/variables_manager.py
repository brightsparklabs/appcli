#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Manages YAML formatted variables files.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
from functools import reduce
from pathlib import Path
from typing import Dict

# vendor libraries
from ruamel.yaml import YAML

# local libraries
from appcli.logger import logger

# ------------------------------------------------------------------------------
# PUBLIC CLASSES
# ------------------------------------------------------------------------------


class VariablesManager:
    """Manages the configuration variables"""

    def __init__(self, configuration_file):
        """Creates a manager for the specified file

        Args:
            configuration_file (str): Path to the configuration file to manage
        """
        self.configuration_file = Path(configuration_file)
        self.yaml = YAML()

        # TODO: We want to be able to read this file in immediately, and allow a 'save' command.

    def get_variable(self, path):
        """Gets a value from the configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
        """
        configuration = self.__get_configuration()
        try:
            return reduce(lambda e, k: e[k], path.split("."), configuration)
        except Exception:
            return ""

    def get_all_variables(self):
        return self.__get_configuration()

    def set_variable(self, path, value):
        """Sets a value in the configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
            value: value for the setting
        """
        configuration = self.__get_configuration()

        path_elements = path.split(".")
        parent_path = path_elements[:-1]

        # ensure parent path exists
        def ensure_path(parent, child):
            if child not in parent:
                parent[child] = {}
            return parent[child]

        reduce(ensure_path, parent_path, configuration)

        # set the value
        parent_element = reduce(lambda e, k: e[k], parent_path, configuration)
        parent_element[path_elements[-1]] = value

        self.__save(configuration)

    def set_all_variables(self, variables: Dict):
        """Sets all values in the configuration

        Args:
            variables (Dict): the variables to set
        """
        self.__save(variables)

    def __get_configuration(self) -> Dict:
        """Get the current configuration from file

        Returns:
            Dict: the current configuration
        """
        try:
            data = self.configuration_file.read_text(encoding="utf-8")
            return self.yaml.load(data)
        except Exception as ex:
            raise Exception(
                f"Could not read configuration file at [{self.configuration_file}]"
            ) from ex

    def __save(self, variables: Dict):
        """Saves the supplied Dict of variables to the configuration file

        Args:
            variables (Dict): the variables to save
        """
        full_path = self.configuration_file.absolute().as_posix()
        logger.info(f"Saving configuration to [{full_path}] ...")
        with open(full_path, "w") as config_file:
            self.yaml.dump(variables, config_file)

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Manages YAML formatted variables files.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard library
import re
from functools import reduce
from pathlib import Path
from typing import Dict, Union

from jinja2 import StrictUndefined, Template

# vendor libraries
from ruamel.yaml import YAML

from appcli.crypto.crypto import decrypt_value

# local libraries
from appcli.logger import logger

# ------------------------------------------------------------------------------
# PUBLIC CLASSES
# ------------------------------------------------------------------------------


class VariablesManager:
    """Manages the configuration variables"""

    def __init__(self, configuration_file, key_file, extra_configuration_files: str):
        """Creates a manager for the specified file

        Args:
            configuration_file (str): Path to the configuration file to manage.
            extra_configuration_files (str): Path to a directory containing extra configuration files.
        """
        self.configuration_file = Path(configuration_file)
        self.key_file = Path(key_file)
        self.extra_configuration_files = Path(extra_configuration_files)
        self.yaml = YAML()

        # TODO: We want to be able to read this file in immediately, and allow a 'save' command.

    def get_variable(self, path: str, decrypt: bool = False):
        """Gets a value from the configuration.

        Args:
            path (str): Dot notation for the setting. E.g. settings.insilico.external.database.host
            decrypt (bool): Optional (defaults to False). Whether to decrypt the returned value (if it's encrypted).

        Throws:
            Exception: Failed to find the configuration key.
        """
        configuration = self.__get_configuration()
        try:
            variable = reduce(lambda e, k: e[k], path.split("."), configuration)
        except KeyError as exc:
            raise KeyError(f"Setting [{path}] not set in configuration.") from exc

        if decrypt:
            variable = decrypt_value(variable, key_file=self.key_file)

        return variable

    def get_all_variables(self):
        return self.__get_configuration()

    def set_variable(self, path: str, value: Union[str, bool, int, float]):
        """Sets a value in the configuration

        Type of value is not enforced but this might not serialise into yml in a deserialisable format.

        Args:
            path (str): Dot notation for the setting. E.g. settings.insilico.external.database.host
            value: value for the setting

        TODO: warn user if attempting to save variable not in main config.
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
        """Get the current configuration from file(s)

        Returns:
            Dict: the current configuration

        """
        config_variables_main = self.__get_configuration_main()
        config_variables = self.__get_configuration_extra(config_variables_main)
        return config_variables_main | config_variables

    def __get_configuration_main(self) -> Dict:
        """Gets the configuration from the main `settings.yml` file.

        Returns:
            Dict: The configuration data from the main configuration file.
        """
        config_variables_main = dict()
        try:
            data_string = self.__read_configuration_source(self.configuration_file)
            config_variables_main |= self.__convert_yaml_to_dict(
                data_string, self.configuration_file.stem
            )
        except Exception as ex:
            raise Exception(
                f"Could not read main configuration file at [{self.configuration_file}]"
            ) from ex
        return config_variables_main

    def __get_configuration_extra(self, variables: Dict) -> Dict:
        """Gets the configuration from the additional configuration files.

        Args:
            variables (Dict): Variables used to populate the template(s).

        Returns:
            Dict: The configuration data from the additional configuration files.
                Each config file is a seperate dictionary with its filename as the key.
        """
        config_variables = dict()
        for config_file in self.extra_configuration_files.glob("*"):
            try:
                data_string = self.__read_configuration_source(config_file)
                if config_file.endswith(".j2"):  # Jinja2 file.
                    data_string = self.__convert_jinja_to_yaml(data_string, variables)
                config_variables |= self.__convert_yaml_to_dict(
                    data_string, config_file.stem
                )
            except Exception as ex:
                raise Exception(
                    f"Could not read configuration file at [{config_file}]"
                ) from ex
        return config_variables

    def __save(self, variables: Dict):
        """Saves the supplied Dict of variables to the configuration file

        Args:
            variables (Dict): All the variables to save (main config dictionary will be extracted).
        """
        variables = variables[self.configuration_file.stem]
        full_path = self.configuration_file.absolute().as_posix()
        logger.debug(f"Saving configuration to [{full_path}] ...")
        with open(full_path, "w") as config_file:
            self.yaml.dump(variables, config_file)

    def __read_configuration_source(self, configuration_filename: Path) -> str:
        """Reads the given configuration file and returns its contents as a string

        Args:
            configuration_filename (Path): The location of the file to read from.

        Returns:
            str: A utf-8 encoded string of the files contents.

        """
        return self.configuration_file.read_text(encoding="utf-8")

    def __convert_jinja_to_yaml(self, jinja_source: str, variables: Dict) -> str:
        """Loads configuration data from a jinja2 string and applies
            the provided templates.

        Args:
            jinja_source (str): A utf-8 encoding of the contents of the jinja2 file.
            variables (Dict): Variables used to populate the template.

        Returns:
            str: A yaml string that has been templated with the provided variables.
        """
        template = Template(
            jinja_source,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return template.render(variables)

    def __convert_yaml_to_dict(self, yaml_source: str, namespace: str) -> Dict:
        """Loads configuration data from a provided yaml string.

        Args:
            yaml_source (str): A utf-8 encoding of some yaml data.
            namespace (str): A unique namespace for this set of data.

        Returns:
            Dict: Configuration data from the file.
        """
        if not re.compile(r"[a-zA-Z0-9_]+").match(namespace):
            raise Exception(f"[{namespace}] conatins invalid characters.")
        yaml_data: dict = {namespace: self.yaml.load(yaml_source)}

        # If the file is empty, the YAML library will load as `None`. Since
        # we expect this function to return a valid dict, we return an
        # empty dictionary if it's empty.
        if yaml_data is None:
            return {}
        return yaml_data

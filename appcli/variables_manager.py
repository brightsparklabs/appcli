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

    def __init__(self, configuration_file: Union[str, Path], key_file, extra_configuration_dir: Union[str, Path] = None,):
        """Creates a manager for the specified file

        Args:
            configuration_file (str): Path to the configuration file to manage.
            extra_configuration_dir (str): Path to a directory containing extra configuration files.
        """
        self.configuration_file = Path(configuration_file)
        self.key_file = Path(key_file)
        if extra_configuration_dir is not None:
            if not Path(extra_configuration_dir).is_dir():
                raise Exception(
                    f"Extra config dir {extra_configuration_dir} is not accessible"
                )
            self.extra_configuration_files = Path(extra_configuration_dir).glob("*")
        else:
            self.extra_configuration_files = []
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
        configuration = self._get_configuration()
        try:
            variable = reduce(lambda e, k: e[k], path.split("."), configuration)
        except KeyError as exc:
            raise KeyError(f"Setting [{path}] not set in configuration.") from exc

        if decrypt:
            variable = decrypt_value(variable, key_file=self.key_file)

        return variable

    def get_all_variables(self):
        return self._get_configuration()

    def set_variable(self, path: str, value: Union[str, bool, int, float]):
        """Sets a value in the configuration

        Type of value is not enforced but this might not serialise into yml in a deserialisable format.

        Args:
            path (str): Dot notation for the setting. E.g. settings.insilico.external.database.host
            value: value for the setting

        TODO: warn user if attempting to save variable outside of the main config file.
        TODO: remember to do unit testing for nested variables etc...
        """
        configuration = self._get_main_configuration()
        path_elements = path.split(".")  # Divide path into array.
        # Iterate through each context on path, to create a recursive dictionary.
        # Main is a pointer to top dictionary object.
        # Sub is a pointer to the current dictionary layer.
        dictionary_main = dictionary_sub = {}
        for field in path_elements:
            # Apply value to bottom dictionary only.
            dictionary_sub[field] = value if field is path_elements[-1] else {}
            dictionary_sub = dictionary_sub[
                field
            ]  # Move sub pointer to next layer down.

        def recursive_dictionary_merge(d1: Dict, d2: Dict):
            # Base case (either d1 or d2 is value).
            if not hasattr(d1, "copy") or not hasattr(d2, "copy"):
                return d2  # d2 overwrites fields in d1.
            d0 = d1.copy()  # New return dictionary.
            for sub in d2.keys():
                if sub not in d1.keys():  # Item isn't a duplicate.
                    d0 |= {sub: d2.get(sub)}
                else:  # Item is a duplicate.
                    d0 |= {sub: recursive_dictionary_merge(d1.get(sub), d2.get(sub))}
            return d0

        self._save(
            recursive_dictionary_merge(configuration, dictionary_main)[
                self.configuration_file.stem
            ]
        )

    def set_all_variables(self, variables: Dict):
        """Sets all values in the configuration

        Args:
            variables (Dict): the variables to set
        """
        self._save(variables[self.configuration_file.stem])

    def _get_configuration(self) -> Dict:
        """Get the current configuration from file(s)

        Returns:
            Dict: the current configuration

        """
        main_configuration_variables = self._get_main_configuration()
        extra_configuration_variables = self._get_extra_configuration(
            main_configuration_variables
        )
        return main_configuration_variables | extra_configuration_variables

    def _get_main_configuration(self) -> Dict:
        """Gets the configuration from the main `settings.yml` file.

        Throws:
            Exception: Unable to read the configuration file.

        Returns:
            Dict: The configuration data from the main configuration file.
        """
        config_variables_main = dict()
        try:
            data_string = self.configuration_file.read_text(encoding="utf-8")
        except Exception as ex:
            raise Exception(
                f"Could not read main configuration file at [{self.configuration_file}]"
            ) from ex
        config_variables_main |= self._convert_yaml_to_dict(
            data_string, self.configuration_file.stem
        )
        return config_variables_main

    def _get_extra_configuration(self, variables: Dict) -> Dict:
        """Gets the configuration from the additional configuration files.

        Args:
            variables (Dict): Variables used to populate the template(s).

        Throws:
            Exception:
                Unable to read the configuration file.
                Could not correctly render a jinja2 template.

        Returns:
            Dict: The configuration data from the additional configuration files.
                Each config file is a seperate dictionary with its filename as the key.
        """
        config_variables = dict()
        for config_file in self.extra_configuration_files:
            try:
                data_string = config_file.read_text(encoding="utf-8")
            except Exception as ex:
                raise Exception(
                    f"Could not read configuration file at [{config_file}]"
                ) from ex
            if config_file.suffix == ".j2":  # Jinja2 file.
                try:
                    data_string = self._render_j2(data_string, variables)
                except Exception as ex:
                    raise Exception(
                        f"There was a problem rendering the jinja2 file at [{config_file}]"
                    ) from ex
            config_variables |= self._convert_yaml_to_dict(
                data_string, config_file.stem
            )
        return config_variables

    def _save(self, variables: Dict):
        """Saves the supplied Dict of variables to the configuration file

        Args:
            variables (Dict): All the variables to save.
        """
        full_path = self.configuration_file.absolute().as_posix()
        logger.debug(f"Saving configuration to [{full_path}] ...")
        with open(full_path, "w") as config_file:
            self.yaml.dump(variables, config_file)

    def _render_j2(self, jinja_source: str, variables: Dict) -> str:
        """Loads configuration data from a jinja2 string and applies
            the provided templates.

        Args:
            jinja_source (str): A utf-8 encoding of the contents of the jinja2 file.
            variables (Dict): Variables used to populate the template.

        Returns:
            str: A string that has been templated with the provided variables.
        """
        template = Template(
            jinja_source,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return template.render(variables)

    def _convert_yaml_to_dict(self, yaml_source: str, namespace: str) -> Dict:
        """Loads configuration data from a provided yaml string.

        Args:
            yaml_source (str): A utf-8 encoding of some yaml data.
            namespace (str): A unique namespace for this set of data.

        Throws:
            Exception: The namespace contains invalid character(s).

        Returns:
            Dict: Configuration data from the file.
        """
        if not self._is_namespace_valid(namespace):
            raise Exception(f"[{namespace}] contains invalid characters.")
        return {namespace: self.yaml.load(yaml_source)}

    def _is_namespace_valid(self, namespace: str) -> bool:
        """Checks if the given string can be used as a key in a dictionary.
           A valid namespace can only contain [a-zA-Z0-9_].

        Args:
            namespace (str): The namespace to check the characters of.

        Returns:
            bool: True for a valid namespace, otherwise false.
        """
        return re.compile(r"[a-zA-Z0-9_]+").match(namespace)

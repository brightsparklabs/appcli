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

    def __init__(
        self,
        configuration_file: Path,
        key_file: Path = None,
        stack_configuration_file: Path = None,
        extra_configuration_dir: Path = None,
    ):
        """A class which enables get, set, save for configuration variables of the application.

        Args:
            configuration_file (Path): Path to the main configuration file.
            key_file (Path): Optional. Path to the key file for encryption.
            stack_configuration_file (Path): Optional. Path to the stack configuration file.
            extra_configuration_dir (Path): Optional. Path to a directory containing extra configuration files.
        """
        self.configuration_file = Path(configuration_file)
        self.key_file = Path(key_file) if key_file is not None else None
        self.stack_configuration_file = (
            Path(stack_configuration_file)
            if stack_configuration_file is not None
            else None
        )

        # If extra configuration directory is not set or doesn't exist, assume there's no extra configuration.
        if (extra_configuration_dir is None) or (
            not Path(extra_configuration_dir).is_dir()
        ):
            self.extra_configuration_files = []
            logger.debug("No additional configuration files found.")
        else:
            self.extra_configuration_files = Path(extra_configuration_dir).glob("*")
            logger.debug(
                f"Found extra configuration files [{self.extra_configuration_files}]."
            )

        self.yaml = YAML()

    ############################################################################
    # MAIN CONFIGURATION FUNCTIONS
    ############################################################################

    def get_variable(self, path: str, decrypt: bool = False):
        """Gets a value from the main configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
            decrypt (bool): Optional (defaults to False). Whether to decrypt the returned value (if it's encrypted).

        Throws:
            Exception: Failed to find the configuration key.
        """
        main_configuration = self._get_main_configuration()
        return self._get_variable_from_dict(path, main_configuration, decrypt)

    def get_all_variables(self):
        return self._get_main_configuration()

    def set_variable(self, path: str, value: Union[str, bool, int, float]):
        """Sets a value in the configuration.
        Type of value is not enforced but this might not serialise into yml in a deserialisable format.
        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
            value: value for the setting
        """
        configuration = self._get_main_configuration()

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

        self._save(configuration)

    def set_all_variables(self, variables: Dict):
        """Sets all values in the configuration

        Args:
            variables (Dict): the variables to set
        """
        self._save(variables)

    def _get_main_configuration(self) -> Dict:
        """Gets the configuration from the main `settings.yml` file.

        Throws:
            Exception: Unable to read the configuration file.

        Returns:
            Dict: The configuration data from the main configuration file.
        """
        return self._load_yaml_to_dict(self.configuration_file)

    def _save(self, variables: Dict):
        """Saves the supplied Dict of variables to the configuration file.

        Args:
            variables (Dict): All the variables to save.
        """
        full_path = self.configuration_file.absolute().as_posix()
        logger.debug(f"Saving configuration to [{full_path}] ...")
        with open(full_path, "w") as config_file:
            self.yaml.dump(variables, config_file)

    ############################################################################
    # STACK CONFIGURATION FUNCTIONS
    ############################################################################

    def get_stack_variable(self, path: str, decrypt: bool = False):
        """Gets a value from the stack configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
            decrypt (bool): Optional (defaults to False). Whether to decrypt the returned value (if it's encrypted).

        Throws:
            Exception: Failed to find the configuration key.
        """
        stack_configuration = self._get_stack_configuration()
        return self._get_variable_from_dict(path, stack_configuration, decrypt)

    def _get_stack_configuration(self) -> Dict:
        """Gets the configuration from the stack configuration `stack-settings.yml` file.

        Throws:
            Exception: Unable to read the configuration file.

        Returns:
            Dict: The configuration data from the stack configuration file.
        """
        return self._load_yaml_to_dict(self.stack_configuration_file)

    ############################################################################
    # TEMPLATING CONFIGURATION FUNCTIONS
    ############################################################################

    def get_templating_configuration(self) -> Dict:
        """Get the current configuration from file(s)

        Returns:
            Dict: the current configuration

        """
        main_configuration_variables = self._get_main_configuration()
        extra_configuration_variables = self._get_extra_configuration(
            main_configuration_variables
        )
        # TODO: Figure out namespacing
        return main_configuration_variables | extra_configuration_variables

    ############################################################################
    # COMMON FUNCTIONS
    ############################################################################

    def _get_variable_from_dict(self, path: str, data: Dict, decrypt: bool = False):
        try:
            variable = reduce(lambda e, k: e[k], path.split("."), data)
        except KeyError as exc:
            raise KeyError(f"Setting [{path}] not set in configuration.") from exc

        if decrypt:
            variable = decrypt_value(variable, key_file=self.key_file)

        return variable

    def _load_yaml_to_dict(self, data: str) -> Dict:
        yaml_data = self.yaml.load(data)
        if yaml_data is None:
            return {}
        return yaml_data

    def _load_yaml_file_to_dict(self, file: Path) -> Dict:
        """Reads in a YAML file into a Dict.

        Throws:
            Exception: Unable to read the file.

        Returns:
            Dict: The yaml data as a Dict.
        """
        if file is None:
            return {}

        try:
            raw_data = file.read_text(encoding="utf-8")
            return self._load_yaml_to_dict(raw_data)

        except Exception as ex:
            raise Exception(f"Could not read file at [{file}]") from ex

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
            # Validate config_file.stem is a valid key in YAML
            config_file_yaml_key = config_file.stem
            regex = "^[a-zA-Z0-9_.]+$"
            if re.match(regex, config_file_yaml_key) is None:
                raise Exception(
                    f"Could not use extra config file name [{config_file_yaml_key}] as yaml key."
                )

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
                        f"Failed to render Jinja2 file [{config_file}]"
                    ) from ex
            config_variables |= {config_file.stem: self._load_yaml_to_dict(data_string)}
        return config_variables

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

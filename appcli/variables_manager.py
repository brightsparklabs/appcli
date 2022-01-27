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
from typing import Dict, Iterable, Union

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

    def __init__(self, configuration_file, key_file, extra_configuration_files: Iterable[str] = []):
        """Creates a manager for the specified file

        Args:
            configuration_file (str): Path to the configuration file to manage.
            extra_configuration_files (Iterable[str]): Path to extra configuration files to load.
        """
        self.configuration_file = Path(configuration_file)
        self.key_file = Path(key_file)
        self.extra_configuration_files = list(map(Path, extra_configuration_files))
        self.yaml = YAML()

        # TODO: We want to be able to read this file in immediately, and allow a 'save' command.

    def get_variable(self, path: str, decrypt: bool = False):
        """Gets a value from the configuration.

        Args:
            path (str): Dot notation for the setting. E.g. insilico.external.database.host
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
        """Sets a value in the configuration.

        Type of value is not enforced but this might not serialise into yml in a deserialisable format.

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
        """Get the current configuration from file(s)

        Returns:
            Dict: the current configuration

        TODO:
            Change dict update functions to `=|` once the python interpreter accepts it (v3.9+).
        """
        config_variables = dict()
        try:  # Read the main configuration file.
            config_variables.update(load_yml(self.configuration_file, self.yaml))
        except Exception as ex:
            raise Exception(
                f"Could not read configuration file at [{self.configuration_file}]"
            ) from ex
        for file in self.extra_configuration_files:  # Read extra configuration files.
            if file.endswith(".yml"):  # Yaml file.
                try:
                    config_variables.update(load_yml(file, self.yaml))
                except Exception as ex:
                    raise Exception(
                        f"Could not read configuration file at [{file}]"
                    ) from ex
            elif file.endswith(".j2"):  # Jinja2 file.
                try:
                    config_variables.update(load_j2(file, self.yaml, config_variables))
                except Exception as ex:
                    raise Exception(
                        f"Could not read configuration file at [{file}]"
                    ) from ex
            else:  # Unknown file type.
                raise Exception(f"Unknown filetype [{file}]")
        return config_variables

    def __save(self, variables: Dict):
        """Saves the supplied Dict of variables to the configuration file

        Args:
            variables (Dict): the variables to save
        """
        full_path = self.configuration_file.absolute().as_posix()
        logger.debug(f"Saving configuration to [{full_path}] ...")
        with open(full_path, "w") as config_file:
            self.yaml.dump(variables, config_file)


def load_yml(filename: Path, yaml: YAML) -> Dict:
    """Loads configuration data from a yaml file (yml).

    Args:
        filename (Path): The location of the file to read from.
        yaml (YAML): A yaml object to use as the parser.

    Returns:
        Dict: Configuration data from the file.
    """
    raw_data = filename.read_text(encoding="utf-8")
    yaml_data = yaml.load(raw_data)
    yaml_data = dict(  # Append filename to keys for namespacing.
        zip(
            list([filename.stem + "." + key for key in yaml_data.keys()]),
            list(yaml_data.values()),
        )
    )
    # If the file is empty, the YAML library will load as `None`. Since
    # we expect this function to return a valid dict, we return an
    # empty dictionary if it's empty.
    if yaml_data is None:
        return {}
    return yaml_data


def load_j2(filename: Path, yaml: YAML, variables: dict) -> Dict:
    """Loads configuration data from a jinja2 file (j2).

    Args:
        filename (Path): The location of the file to read from.
        yaml (YAML): A yaml object to use as the parser.
        variables (dict): Variables used to populate the template.

    Returns:
        Dict: Configuration data from the file.
    """
    template = Template(
        filename.read_text(),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    output_text = template.render(variables)
    yaml_filename = ".".join(filename.split(".")[:-1])  # Remove .j2 from extension.
    yaml_filename.write_text(output_text)  # Write to .yml file.
    return load_yml(yaml_filename, yaml)

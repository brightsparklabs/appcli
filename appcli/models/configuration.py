#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, Dict, FrozenSet, Iterable, NamedTuple, Tuple

# vendor libraries
import click

# local libraries
from appcli.orchestrators import Orchestrator


class Hooks(NamedTuple):
    """ Hooks to run before/after stages """

    migrate_variables: Callable[[Dict, str, Dict], Dict] = lambda x, y, z: x
    """ Optional. Delegate function to run during a migration, which converts variables between application versions.
     Args are: [Dict of variables to transform], [version of the current variables], and [Dict of clean variables
     at the new application version]. Returns [transformed Dict of variables]. If no function provided, identity
     function is used."""
    is_valid_variables: Callable[
        [Dict, Dict], bool
    ] = lambda x, y: is_matching_dict_structure(x, y)
    """ Validate a Dict of variables are valid for use in the current application version. Args are: [Dict of the
    variables to validate], and [Dict of the current version's clean variables]. Returns True if the
    Dict to validate is valid for the application at the current version. """
    pre_start: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'start'. """
    post_start: Callable[[click.Context, CompletedProcess], None] = lambda x, y: None
    """ Optional. Hook function to run after running 'start'. """
    pre_stop: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'stop'. """
    post_stop: Callable[[click.Context, CompletedProcess], None] = lambda x, y: None
    """ Optional. Hook function to run after running 'stop'. """
    pre_configure_init: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'configure init'. """
    post_configure_init: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run after running 'configure init'. """
    pre_configure_apply: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'configure apply'. """
    post_configure_apply: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run after running 'configure apply'. """


class Configuration(NamedTuple):
    """ Configuration for building the CLI. """

    app_name: str
    """ Name of the application (do not use spaces). """

    docker_image: str
    """ The docker image used to run the CLI. """

    seed_app_configuration_file: Path
    """
    Path to a seed YAML file containing variables which are applied to the
    templates to generate the final configuration files.
    """

    seed_templates_dir: Path
    """
    Seed directory containing jinja2 templates used to generate the final
    configuration files.
    """

    orchestrator: Orchestrator
    """ Orchestrator to use to launch Docker containers. """

    hooks: Hooks = Hooks()
    """ Optional. Hooks to run before/after stages. """

    custom_commands: Iterable[Callable] = frozenset()
    """
    Optional. Extra click commands to add to the CLI. Can be group or specific commands.
    """

    mandatory_additional_data_dirs: FrozenSet[Tuple[str, Path]] = frozenset()
    """
    Optional. Additional data directories which must be supplied.
    """

    mandatory_additional_env_variables: FrozenSet[Tuple[str, Path]] = frozenset()
    """
    Optional. Additional environment variables which must be supplied.
    """

    decrypt_generated_files: Iterable[str] = frozenset()
    """
    Optional. Generated files which should be forcibly decrypted. It is
    generally bad practice to do this unless a post hook re-encrypts the
    generated files. Paths are relative and will be resolved against the
    generated configuration directory.
    """


def is_matching_dict_structure(dict_to_validate: Dict, clean_dict: Dict):
    """Validate the structure of a Dict against another Dict. Recursively checks the keys and
    types of the values match for all Dicts in the base Dict, relative to the clean dict.

    Args:
        dict_to_validate (Dict): the dict to validate
        clean_dict (Dict): the clean dict to validate against
    """
    # Pop the root 'custom' blocks so they aren't compared by default
    dict_to_validate.pop("custom", None)
    clean_dict.pop("custom", None)
    return are_dicts_matching_structure(dict_to_validate, clean_dict,)


def are_dicts_matching_structure(dict_1: Dict, dict_2: Dict) -> bool:
    """Recursively checks if the keys of the first dictionary match the keys of the second, as well
    as their value types.

    Args:
        dict_1 (Dict): first dict to compare
        dict_2 (Dict): second dict to compare

    Returns:
        bool: True if the Dict keys and value types match, else False
    """
    # If the set of keys isn't matching, these dicts don't "match"
    if dict_1.keys() != dict_2.keys():
        return False

    for key in dict_1.keys():
        # If the type of key_x in dict_1 doesn't match the type of the same key in dict_2, the
        # dicts don't match
        if not isinstance(dict_2[key], type(dict_1[key])):
            return False

        # If it's a dict type, recurse
        if isinstance(dict_1[key], dict):
            if not are_dicts_matching_structure(dict_1[key], dict_2[key]):
                return False

    return True

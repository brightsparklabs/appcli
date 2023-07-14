#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
import inspect
import os
import re
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, Dict, FrozenSet, Iterable, NamedTuple

# vendor libraries
import click
from pydantic import BaseModel

# local libraries
from appcli.orchestrators import DockerComposeOrchestrator, Orchestrator


class Hooks(NamedTuple):
    """Hooks to run before/after stages"""

    migrate_variables: Callable[
        [click.Context, Dict, str, Dict], Dict
    ] = lambda w, x, y, z: x
    """ Optional. Delegate function to run during a migration, which converts variables between application versions.
     Args are: CLI context, [Dict of variables to transform], [version of the current variables], and [Dict of clean variables
     at the new application version]. Returns [transformed Dict of variables]. If no function provided, identity
     function is used."""
    is_valid_variables: Callable[
        [click.Context, Dict, Dict], bool
    ] = lambda w, x, y: True
    """ Validate a Dict of variables are valid for use in the current application version.
      Args are: CLI context, [Dict of the variables to validate], and [Dict of the current version's clean variables]. Returns
      True if the Dict to validate is valid for the application at the current version.
      Default is to always pass validation."""
    pre_start: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'start'. """
    post_start: Callable[[click.Context, CompletedProcess], None] = lambda x, y: None
    """ Optional. Hook function to run after running 'start'. """
    pre_shutdown: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'shutdown'. """
    post_shutdown: Callable[[click.Context, CompletedProcess], None] = lambda x, y: None
    """ Optional. Hook function to run after running 'shutdown'. """
    pre_configure_init: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'configure init'. """
    post_configure_init: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run after running 'configure init'. """
    pre_configure_apply: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run before running 'configure apply'. """
    post_configure_apply: Callable[[click.Context], None] = lambda x: None
    """ Optional. Hook function to run after running 'configure apply'. """


class Configuration(BaseModel):
    """Configuration for building the CLI."""

    app_name: str
    """ Name of the application (do not use spaces). """

    docker_image: str
    """ The docker image used to run the CLI. """

    seed_app_configuration_file: Path = Path(
        os.path.dirname(
            inspect.stack()[-1].filename
        ),  # Filename at the top of the call-stack.
        "resources/settings.yml",
    )
    """
    Path to a seed YAML file containing variables which are applied to the
    templates to generate the final configuration files.
    """

    stack_configuration_file: Path = Path(
        os.path.dirname(
            inspect.stack()[-1].filename
        ),  # Filename at the top of the call-stack.
        "resources/stack-settings.yml",
    )
    """
    Path to the stack configuration file which contains variables which are used to
    configure the stack.
    """

    baseline_templates_dir: Path = Path(
        os.path.dirname(
            inspect.stack()[-1].filename
        ),  # Filename at the top of the call-stack.
        "resources/templates/baseline",
    )
    """
    Directory containing the baseline set of jinja2 templates used to generate the final
    configuration files. These template files are expected to remain static and should
    only be overridden as a hotfix.
    """

    orchestrator: Orchestrator = DockerComposeOrchestrator(
        docker_compose_file=Path("docker-compose.yml"),
        docker_compose_task_file=Path("docker-compose.tasks.yml"),
    )
    """ Orchestrator to use to launch Docker containers. """

    application_context_files_dir: Path = None
    """
    Optional. Path to directory containing YAML files which are applied to
    templates to generate the final configuration files. These application
    context files can be templates themselves, which are rendered by the
    main app configuration file.
    """

    configurable_templates_dir: Path = Path(
        os.path.dirname(
            inspect.stack()[-1].filename
        ),  # Filename at the top of the call-stack.
        "resources/templates/configurable",
    )
    """
    Optional. Directory containing a default initial set of configurable jinja2 templates
    used to generate the final configuration files. These template files are expected to be
    modified as required on a per-deployment basis.
    """

    hooks: Hooks = Hooks()
    """ Optional. Hooks to run before/after stages. """

    custom_commands: Iterable[Callable] = frozenset()
    """
    Optional. Extra click commands to add to the CLI. Can be group or specific commands.
    """

    mandatory_additional_data_dirs: FrozenSet[str] = frozenset()
    """
    Optional. Additional data directories which must be supplied.
    """

    mandatory_additional_env_variables: FrozenSet[str] = frozenset()
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

    auto_configure_on_install: bool = True
    """
    Optional. Whether to run the corresponding install and configure
    commands on the application. Equivalent to:
        docker run --rm brightsparklabs/myapp:<version> install | sudo bash
        /opt/brightsparklabs/myapp/production/myapp configure init
        /opt/brightsparklabs/myapp/production/myapp configure apply
    """

    @property
    def app_name_slug(self) -> str:
        """
        Returns a slug version of the application name which is shell safe.

        This transforms the app_name variable by replacing any unsafe shell
        characters with '_', and returning the new string.
        Safe characters are: [a-z],[A-Z],[0-9] or '_'.
        First character cannot be [0-9].
        https://unix.stackexchange.com/questions/428880/list-of-acceptable-initial-characters-for-a-bash-variable
        https://linuxhint.com/bash-variable-name-rules-legal-illegal/
        """
        return "".join(
            [
                re.sub(r"[^a-zA-Z_]", "_", self.app_name[0]),  # First character.
                re.sub(r"[^a-zA-Z0-9_]", "_", self.app_name[1:]),
            ]
        )

    model_config: dict = {"arbitrary_types_allowed": True}
    """
    This is a requirement for pydantic to disable type checking for arbitrary user types for fields.
    This is necessary as one or more of the fields are custom classes (e.g. Orchestrator).
    NOTE: This was updated in `pydantic==2.0`.
    See class attribute
    """


def is_matching_dict_structure(dict_to_validate: Dict, clean_dict: Dict):
    """Validate the structure of a Dict against another Dict. Recursively checks the keys and
    types of the values match for all Dicts in the base Dict, relative to the clean dict.

    TODO: (Github issue #77) This should be used as the default function for
    `Hooks.is_valid_variables` however it was causing us some migration issues.
    This function and subfunction(s) need more error logging to describe why it fails,
    and we need to fix it to make it more reliable.

    Args:
        dict_to_validate (Dict): the dict to validate
        clean_dict (Dict): the clean dict to validate against
    """
    # Pop the root 'custom' blocks so they aren't compared by default
    dict_to_validate.pop("custom", None)
    clean_dict.pop("custom", None)
    return are_dicts_matching_structure(
        dict_to_validate,
        clean_dict,
    )


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

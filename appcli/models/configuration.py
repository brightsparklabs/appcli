#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Configuration for building the CLI.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import inspect
import os
import re
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, NamedTuple, Optional

# vendor libraries
import click
from pydantic import BaseModel

# local libraries
from appcli.orchestrators import DockerComposeOrchestrator, Orchestrator
from appcli.models.cli_context import CliContext


class Hooks(NamedTuple):
    """Hooks to run before/after stages"""

    migrate_variables: Callable[
        [CliContext, Dict[str, Any], str, Dict[str, Any]], Dict[str, Any]
    ] = lambda w, x, y, z: x
    """ Optional. Delegate function to run during a migration, which converts
    variables between application versions. Essentially this provides you the
    extant variables from the `settings.yml` file along with some context, and
    allows you to transform them as needed to work on the new version of the
    system. The resulting dictionary is serialised to create the new
    `settings.yml` file.

    You can get the new version of the system via: `cli_context.app_version`.

    If no function provided, the variables are returned unchanged.

     Args:
         CliContext: The appcli context.
         Dict[str, Any]: The variables to be transformed. I.e. the variables
           from the extant `settings.yml` file.
         str: The version of the system that the extant `settings.yml` file
           pertained to. I.e. the `settings.yml` file 'works' for that version
           of the system.
         Dict[str, Any]: The default variables from the new `settings.yml`
           file. I.e. the `settings.yml` file present by default on the new
           version we are migrating to.

    Returns:
        Dict[str, Any]: The variables to use to create the new `setting.yml`
          file.
     """

    is_valid_variables: Callable[[CliContext, Dict[str, Any], Dict[str, Any]], bool] = (
        lambda w, x, y: True
    )
    """ Validate a Dict of variables are valid for use in the current
    application version.

    Default is to always pass validation.

    Args:
         CliContext: The appcli context.
         Dic[str, Any]t: The variables to validate. I.e. the variables from the
           current `settings.yml` file.
         Dic[str, Any]t: The default variables from the `settings.yml` of the
           current version of the system. I.e. the `settings.yml` file present
           by default on the current version of the system we are running.

    Returns:
        True if the variables are valid for the version of the system we are
        running.
    """

    pre_start: Callable[[click.Context], None] = lambda x: None
    """
    [Optional] Hook function to run before running 'start'.

    Args:
        Arg[0] (click.Context): The click context object.
    """

    post_start: Callable[[click.Context, CompletedProcess], None] = lambda x, y: None
    """
    [Optional] Hook function to run after running 'start'.

    Args:
        Arg[0] (click.Context): The click context object.
        Arg[1] (CompletedProcess): The process result object from running `start`.
    """

    pre_shutdown: Callable[[click.Context], None] = lambda x: None
    """
    [Optional] Hook function to run before running 'shutdown'.

    Args:
        Arg[0] (click.Context): The click context object.
    """

    post_shutdown: Callable[[click.Context, CompletedProcess], None] = lambda x, y: None
    """
    [Optional] Hook function to run after running 'shutdown'.

    Args:
        Arg[0] (click.Context): The click context object.
        Arg[1] (CompletedProcess): The process result object from running `shutdown`.
    """

    pre_configure_init: Callable[[click.Context, Optional[str]], None] = (
        lambda x, y: None
    )
    """
    [Optional] Hook function to run before running 'configure init'.

    Args:
        Arg[0] (click.Context): The click context object.
        Arg[1] (Optional[str]): The supplied `--preset` arg.
    """

    post_configure_init: Callable[[click.Context, Optional[str]], None] = (
        lambda x, y: None
    )
    """
    [Optional] Hook function to run after running 'configure init'.

    Args:
        Arg[0] (click.Context): The click context object.
        Arg[1] (Optional[str]): The supplied `--preset` arg.
    """

    pre_configure_apply: Callable[[click.Context], None] = lambda x: None
    """
    [Optional] Hook function to run before running 'configure apply'.

    Args:
        Arg[0] (click.Context): The click context object.
    """

    post_configure_apply: Callable[[click.Context], None] = lambda x: None
    """
    [Optional] Hook function to run after running 'configure apply'.

    Args:
        Arg[0] (click.Context): The click context object.
    """


class PresetsConfiguration(BaseModel):
    """Settings for loading preconfigured defaults."""

    is_mandatory: bool = False
    """Whether the system supports/enforces using presets."""

    templates_directory: Path = Path(
        os.path.dirname(
            inspect.stack()[-1].filename
        ),  # Filename at the top of the call-stack.
        "resources/templates/presets",
    )
    """Directory containing the preset profiles."""

    default_preset: Optional[str] = None
    """The default preset to use if one is not supplied."""

    def get_options(self) -> List[str]:
        """
        Return the list of presets.

        Returns:
            List[str]: The list of preset names available.
        """
        return [
            preset.name
            for preset in self.templates_directory.iterdir()
            if preset.is_dir()
        ]


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

    presets: PresetsConfiguration = PresetsConfiguration()
    """Settings for loading preconfigured defaults."""


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

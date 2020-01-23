#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, FrozenSet, Iterable, NamedTuple, Tuple, Dict

# vendor libraries
import click

# local libraries
from appcli.orchestrators import Orchestrator


class Hooks(NamedTuple):
    """ Hooks to run before/after stages """

    migrate_variables: Callable[[Dict, str], Dict] = lambda x, y: x
    """ Optional. Delegate function to run during a migration, which converts variables between application versions.
     Args are: [Dict of variables to transform], and [version of the current variables file]. Returns
     [transformed Dict of variables]. If no function provided, identity function is used."""
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

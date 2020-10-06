#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for configuration manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from pathlib import Path

# vendor libraries
import pytest

from appcli import CliContext, Configuration, DockerComposeOrchestrator

# local libraries
from appcli.configuration_manager import (
    ConfigurationManager,
    confirm_generated_configuration_is_using_current_configuration,
)

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "test_app"

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_initialise(tmpdir):
    conf_manager = create_conf_manager(tmpdir)

    # Don't expect any errors
    conf_manager.initialise_configuration()

    # Check the variables file has been copied
    assert Path(tmpdir, "conf/settings.yml").exists()

    # Check the key has been generated
    assert Path(tmpdir, "conf/key").exists()

    # .generated shouldn't exist yet
    assert not Path(tmpdir, "conf/.generated").exists()

    # overrides directory should not exist on clean initialise
    assert not Path(tmpdir, "conf/overrides").exists()


def test_initialise_on_initialised_repo(tmpdir):
    conf_manager = create_conf_manager(tmpdir)
    conf_manager.initialise_configuration()

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        # Expect that we cannot initialise on an already-initialised repo
        conf_manager.initialise_configuration()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    assert "Configuration already exists" in pytest_wrapped_e.value.__cause__.code


def test_apply_before_init(tmpdir):
    conf_manager = create_conf_manager(tmpdir)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        # Expect that we cannot apply on an uninitialised repo
        conf_manager.apply_configuration_changes(message="some message")
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    assert "Configuration does not exist" in pytest_wrapped_e.value.__cause__.code


def test_migrate_before_init(tmpdir):
    conf_manager = create_conf_manager(tmpdir)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        # Expect that we cannot migrate on an uninitialised repo
        conf_manager.migrate_configuration()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    assert "Configuration does not exist" in pytest_wrapped_e.value.__cause__.code


def test_apply_workflow(tmpdir):
    cli_context = create_cli_context(tmpdir)
    conf_manager = create_conf_manager(tmpdir, cli_context)

    # Initialise the application
    conf_manager.initialise_configuration()

    # Set a variable
    variables_manager = conf_manager.get_variables_manager()
    password_variable_path = "test.identity.password"
    new_password = "securepassword1"
    variables_manager.set_variable(password_variable_path, new_password)

    # Assert that the variable was set
    assert variables_manager.get_variable(password_variable_path) == new_password

    # Apply the configuration
    commit_message = "test commit message"
    conf_manager.apply_configuration_changes(message=commit_message)

    # Assert template files have been generated
    assert Path(tmpdir, "conf/.generated").exists()
    assert Path(tmpdir, "conf/.generated/password_file").exists()
    assert Path(tmpdir, "conf/.generated/password_file").read_text() == new_password
    assert Path(tmpdir, "conf/.generated/baseline_file.txt").exists()
    assert Path(tmpdir, "conf/.generated/nesting/nested_baseline_file.py").exists()

    # This should not raise an exception
    confirm_generated_configuration_is_using_current_configuration(cli_context)


def test_migration(tmpdir):
    cli_context_1 = create_cli_context(tmpdir, app_version="1.0.0")
    conf_manager_1 = create_conf_manager(tmpdir, cli_context_1)

    # Initialise and apply
    conf_manager_1.initialise_configuration()
    conf_manager_1.apply_configuration_changes(message="testing test_migration")

    cli_context_2 = create_cli_context(tmpdir, app_version="2.0.0")
    conf_manager_2 = create_conf_manager(tmpdir, cli_context_2)

    # Expect no error
    conf_manager_2.migrate_configuration()

    # TODO: Asserts on the git repo state?
    # TODO: Asserts on migrated varibles? Should pass in a migration hook function?


def test_migration_same_version(tmpdir):
    cli_context = create_cli_context(tmpdir, app_version="1.0.0")
    conf_manager = create_conf_manager(tmpdir, cli_context)

    # Initialise and apply
    conf_manager.initialise_configuration()
    conf_manager.apply_configuration_changes(
        message="testing test_migration_same_version"
    )

    # Expect no error - migration doesn't throw an error if no migration is required
    conf_manager.migrate_configuration()

    # TODO: Asserts on the git repo state?


# TODO: Test where conf/data directories don't exist
# TODO: Test deliberately failing migrations with migration function hooks

# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_cli_context(tmpdir, app_version: str = "0.0.0") -> CliContext:
    conf_dir = Path(tmpdir, "conf")
    conf_dir.mkdir(exist_ok=True)
    data_dir = Path(tmpdir, "data")
    data_dir.mkdir(exist_ok=True)

    return CliContext(
        configuration_dir=conf_dir,
        data_dir=data_dir,
        additional_data_dirs=None,
        additional_env_variables=None,
        environment="test",
        docker_credentials_file=None,
        subcommand_args=None,
        debug=True,
        app_name=APP_NAME,
        app_version=app_version,
        commands={},
    )


def create_conf_manager(tmpdir, cli_context: CliContext = None) -> ConfigurationManager:

    # If not supplied, create default CliContext.
    if not cli_context:
        cli_context = create_cli_context(tmpdir)

    # directory containing this script
    BASE_DIR = Path(__file__).parent

    configuration = Configuration(
        app_name=APP_NAME,
        docker_image="invalid-image-name",
        seed_app_configuration_file=Path(BASE_DIR, "resources/test_app.yml"),
        baseline_templates_dir=Path(BASE_DIR, "resources/templates/baseline"),
        configurable_templates_dir=Path(BASE_DIR, "resources/templates/configurable"),
        orchestrator=DockerComposeOrchestrator("cli/docker-compose.yml", []),
    )

    return ConfigurationManager(cli_context, configuration)

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

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli import CliContext, Configuration, DockerComposeOrchestrator

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
    assert Path(tmpdir, f"conf/{APP_NAME}.yml").exists()

    # Check the password_file template has been copied
    assert Path(tmpdir, f"conf/templates/password_file.j2").exists()

    # Check the key has been generated
    assert Path(tmpdir, "conf/key").exists()

    # .generated shouldn't exist yet
    assert not Path(tmpdir, "conf/.generated").exists()


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
    conf_manager = create_conf_manager(tmpdir)

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

    # Assert a templated file has been generated
    assert Path(tmpdir, "conf/.generated").exists()
    assert Path(tmpdir, "conf/.generated/password_file").exists()
    assert Path(tmpdir, "conf/.generated/password_file").read_text() == new_password

    # Assert the generated metadata file exists
    assert Path(tmpdir, "conf/.generated/metadata-configure-apply.json").exists()


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_conf_manager(tmpdir) -> ConfigurationManager:
    conf_dir = Path(tmpdir, "conf")
    conf_dir.mkdir()
    data_dir = Path(tmpdir, "data")
    data_dir.mkdir()

    cli_context = CliContext(
        configuration_dir=conf_dir,
        data_dir=data_dir,
        additional_data_dirs=None,
        additional_env_variables=None,
        environment="test",
        subcommand_args=None,
        debug=True,
        app_name=APP_NAME,
        app_version="0.0.0",
        commands={},
    )

    # directory containing this script
    BASE_DIR = Path(__file__).parent

    configuration = Configuration(
        app_name=APP_NAME,
        docker_image="invalid-image-name",
        seed_app_configuration_file=Path(BASE_DIR, "resources/test_app.yml"),
        seed_templates_dir=Path(BASE_DIR, "resources/templates"),
        orchestrator=DockerComposeOrchestrator("cli/docker-compose.yml", []),
    )

    return ConfigurationManager(cli_context, configuration)

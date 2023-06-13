#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for configuration manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import filecmp
from pathlib import Path

# vendor libraries
import pytest

# local libraries
from appcli.configuration_manager import ConfigurationManager
from appcli.models.cli_context import CliContext
from appcli.models.configuration import Configuration
from appcli.orchestrators import DockerComposeOrchestrator

# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

APP_NAME = "Test App"
APP_NAME_SLUG = "Test_App"

# directory containing this script
BASE_DIR = Path(__file__).parent

STACK_CONFIGURATION_FILE = Path(BASE_DIR, "resources/stack_settings.yml")

APP_CONTEXT_FILES_DIR = Path(BASE_DIR, "resources/templates/appcli/context/")

EXPECTED_DIR = Path(BASE_DIR, "expected_generated/")

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


def test_apply_before_init(tmpdir):
    conf_manager = create_conf_manager(tmpdir)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        conf_manager.apply_configuration_changes(message="some message")
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


def test_migrate_before_init(tmpdir):
    conf_manager = create_conf_manager(tmpdir)

    with pytest.raises(
        SystemExit
    ) as pytest_wrapped_e:  # Expect that we cannot migrate on an uninitialised repo
        conf_manager.migrate_configuration()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


def test_apply_workflow(tmpdir):
    cli_context = create_cli_context(tmpdir)
    conf_manager = create_conf_manager(tmpdir, cli_context)

    # Initialise the application
    conf_manager.initialise_configuration()

    # Set a variable
    password_variable_path = "test.identity.password"
    new_password = "securepassword1"
    conf_manager.set_variable(password_variable_path, new_password)

    # Assert that the variable was set
    assert conf_manager.get_variable(password_variable_path) == new_password

    # Apply the configuration
    commit_message = "test commit message"
    conf_manager.apply_configuration_changes(message=commit_message)

    # Assert template files have been generated
    assert Path(tmpdir, "conf/.generated").exists()
    generated_configuration_dir = cli_context.get_generated_configuration_dir()
    assert generated_file_matches_expected(
        generated_configuration_dir, "baseline_file.txt"
    )
    assert generated_file_matches_expected(
        generated_configuration_dir, "docker-compose.tasks.yml"
    )
    assert generated_file_matches_expected(
        generated_configuration_dir, "docker-compose.yml"
    )
    assert generated_file_matches_expected(generated_configuration_dir, "password_file")
    assert generated_file_matches_expected(
        generated_configuration_dir, "references_extra_constants.txt"
    )
    assert generated_file_matches_expected(
        generated_configuration_dir, "references_extra_nonconstants.txt"
    )
    assert generated_file_matches_expected(
        generated_configuration_dir, "nesting/nested_baseline_file.py"
    )


def generated_file_matches_expected(generated_configuration_dir, filepath: str):
    return filecmp.cmp(
        Path(generated_configuration_dir, filepath), Path(EXPECTED_DIR, filepath)
    )


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


def test_migration_maintains_stack_settings(tmpdir):
    default_stack_settings_content = STACK_CONFIGURATION_FILE.read_text()
    new_stack_settings_content = "backups:\n  name: full"

    cli_context_1 = create_cli_context(tmpdir, app_version="1.0.0")
    conf_manager_1 = create_conf_manager(tmpdir, cli_context_1)

    # Initialise and apply
    conf_manager_1.initialise_configuration()
    conf_manager_1.apply_configuration_changes(message="testing test_migration")

    # Verify that the default stack settings file exists and contains default content
    assert (
        cli_context_1.get_stack_configuration_file().read_text()
        == default_stack_settings_content
    )

    # Update contents of the stack settings file
    cli_context_1.get_stack_configuration_file().write_text(new_stack_settings_content)
    conf_manager_1.apply_configuration_changes(message="update stack settings")

    cli_context_2 = create_cli_context(tmpdir, app_version="2.0.0")
    conf_manager_2 = create_conf_manager(tmpdir, cli_context_2)

    # Expect no error
    conf_manager_2.migrate_configuration()

    # Assert that the stack settings file was copied across from the old version
    migrated_stack_settings_content = (
        cli_context_2.get_stack_configuration_file().read_text()
    )
    assert migrated_stack_settings_content == new_stack_settings_content


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
    backup_dir = Path(tmpdir, "backup")
    backup_dir.mkdir(exist_ok=True)

    return CliContext(
        configuration_dir=conf_dir,
        data_dir=data_dir,
        application_context_files_dir=APP_CONTEXT_FILES_DIR,
        additional_data_dirs=None,
        backup_dir=backup_dir,
        additional_env_variables=None,
        environment="test",
        docker_credentials_file=None,
        subcommand_args=None,
        debug=True,
        is_dev_mode=False,
        app_name_slug=APP_NAME_SLUG,
        app_version=app_version,
        commands={},
    )


def create_conf_manager(tmpdir, cli_context: CliContext = None) -> ConfigurationManager:
    # If not supplied, create default CliContext.
    if cli_context is None:
        cli_context = create_cli_context(tmpdir)

    configuration = Configuration(
        app_name=APP_NAME,
        docker_image="invalid-image-name",
        seed_app_configuration_file=Path(BASE_DIR, "resources/settings.yml"),
        application_context_files_dir=APP_CONTEXT_FILES_DIR,
        baseline_templates_dir=Path(BASE_DIR, "resources/templates/baseline"),
        configurable_templates_dir=Path(BASE_DIR, "resources/templates/configurable"),
        orchestrator=DockerComposeOrchestrator("cli/docker-compose.yml", []),
        stack_configuration_file=STACK_CONFIGURATION_FILE,
    )

    return ConfigurationManager(cli_context, configuration)

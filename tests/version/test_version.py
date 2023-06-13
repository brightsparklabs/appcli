#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for `version` command.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
from click.testing import CliRunner

# local libraries
from appcli.commands.version_cli import VersionCli
from appcli.models.cli_context import CliContext


def test_version_cli():
    # Unfortunately, there's no easy way to get access to the main cli command,
    # so we have to test the version command directly. This requires initialising
    # the CliContext into the desired state, including setting the `app_version`.
    # Therefore this unit test doesn't deal with ensuring the `app_version` is
    # correctly populated from within the create_cli function.
    version = "1.2.3"
    cli_context = CliContext(
        configuration_dir=None,
        data_dir=None,
        application_context_files_dir=None,
        additional_data_dirs=None,
        backup_dir=None,
        additional_env_variables=None,
        environment="test",
        docker_credentials_file=None,
        subcommand_args=None,
        debug=True,
        is_dev_mode=False,
        app_name_slug="APP_NAME",
        app_version=f"{version}",
        commands=None,
    )
    runner = CliRunner()
    result = runner.invoke(VersionCli(None).commands["version"], obj=cli_context)
    assert result.exit_code == 0
    assert result.output == f"{version}\n"

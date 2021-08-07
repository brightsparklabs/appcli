#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for version command.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import pytest
from click.testing import CliRunner

# local libraries
from appcli.commands.version_cli import VersionCli


def test_version_cli():
    with pytest.raises(SystemExit) as exit_code:
        runner = CliRunner()
        result = runner.invoke(VersionCli(None).commands["version"]())
        assert exit_code.value.code == 0
        assert result.output == "latest\n"

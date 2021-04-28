#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for configuration state.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import pytest

# local libraries
from appcli.commands.appcli_command import AppcliCommand
from appcli.configuration.configuration_dir_state import (
    CleanConfigurationDirState,
    ConfigurationDirState,
    ConfigurationDirStateFactory,
    DirtyConfAndGenConfigurationDirState,
    DirtyConfConfigurationDirState,
    DirtyGenConfigurationDirState,
    NoDirectoryProvidedConfigurationDirState,
    UnappliedConfigurationDirState,
)

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_no_state():
    """When the conf and generated dirs aren't provided, the only valid command is to install."""
    state = ConfigurationDirStateFactory.get_state(None, None, "1.0.0", None)
    isinstance(state, NoDirectoryProvidedConfigurationDirState)

    state.verify_command_allowed(AppcliCommand.INSTALL)

    # Every command except 'INSTALL' should fail
    for command in AppcliCommand:
        if command is AppcliCommand.INSTALL:
            continue
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            # Expect that we cannot initialise on an already-initialised repo
            state.verify_command_allowed(command)
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1


def test_no_configure_init_on_existing_repos():
    """When the configuration dir exists, do not allow 'configure init'."""

    for state_class in [
        UnappliedConfigurationDirState,
        DirtyConfConfigurationDirState,
        DirtyGenConfigurationDirState,
        DirtyConfAndGenConfigurationDirState,
        CleanConfigurationDirState,
    ]:
        state: ConfigurationDirState = state_class()

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            # Expect that we cannot initialise on an already-initialised repo
            state.verify_command_allowed(AppcliCommand.CONFIGURE_INIT)
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1


# TODO: More ConfigurationDirStateFactory tests
# TODO: Test the more states and the desired outcomes from running commands

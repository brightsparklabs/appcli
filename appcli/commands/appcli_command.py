#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# vendor libraries
import click

# standard libraries
from enum import Enum, auto

"""
Appcli top level common commands and classes.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""


class ArgumentEscapeSequences(click.Command):
    """
    A custom Click Command class that handles the '--' escape sequence.

    It intercepts raw CLI arguments before they reach the standard parser,
    separating everything after the '--' into `ctx.args` while keeping
    standard arguments/options in the primary parsing flow.

    This is used to parse in the extra arguments when we are already using greedy consumption
    for a commands arguments.
    """

    def parse_args(self, ctx, args):
        argument_escape_sequence = "--"
        extra_args = []
        # Check for the presence of the escape sequence in the raw argument list.
        # We find the separator position and hide the following tokens from Click.
        # This prevents the standard parser from crashing on unknown flags.
        if argument_escape_sequence in args:
            separator_index = args.index(argument_escape_sequence)

            # Capture everything following the sequence into a separate list.
            extra_args = args[separator_index + 1 :]

            # Truncate the original args list so the standard parser
            # only processes tokens before the '--'.
            args = args[:separator_index]

        # Invoke the base Click parser.
        # Note: super().parse_args normally clears ctx.args if it finds no unprocessed tokens.
        # It will map the service names to the command's arguments.
        result = super().parse_args(ctx, args)

        # Explicitly re-inject the captured extra arguments into the context.
        # This ensures they are available in `ctx.args` within the command function.
        # IMPORTANT: Do not move this before super().parse_args().
        #
        # Click's internal parser resets `ctx.args` based on the tokens it
        # sees in the above. Because we truncated args to hide the
        # pass through tokens, Click sees this as there are no extra args
        # and will overwrite `ctx.args` with an empty list during the super call.
        #
        # We must manually re-populate `ctx.args` AFTER the parser runs to
        # ensure the passthrough data survives to the command function.
        ctx.args = extra_args
        return result


class AppcliCommand(Enum):
    """
    Enum representing all appcli commands.

    Certain appcli commands cannot be run, or must be forced to run, when the
    configuration directory is in specific states. This enum is used to represent
    appcli commmands to allow the code to determine if the command can be run or
    not.

    For any appcli command that requires the configuration directory to be in
    specific state to run, update this enum if the command is added, deleted, or
    modified.
    """

    CONFIGURE_INIT = auto()
    CONFIGURE_APPLY = auto()
    CONFIGURE_GET = auto()
    CONFIGURE_SET = auto()
    CONFIGURE_DIFF = auto()
    CONFIGURE_EDIT = auto()

    CONFIGURE_TEMPLATE_LS = auto()
    CONFIGURE_TEMPLATE_GET = auto()
    CONFIGURE_TEMPLATE_OVERRIDE = auto()
    CONFIGURE_TEMPLATE_DIFF = auto()

    DEBUG_INFO = auto()

    ENCRYPT = auto()

    INSTALL = auto()

    LAUNCHER = auto()

    MIGRATE = auto()

    SERVICE_START = auto()
    SERVICE_SHUTDOWN = auto()
    SERVICE_LOGS = auto()
    SERVICE_STATUS = auto()

    TASK_RUN = auto()

    ORCHESTRATOR = auto()

    BACKUP = auto()
    RESTORE = auto()
    VIEW_BACKUPS = auto()

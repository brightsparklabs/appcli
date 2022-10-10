#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Enum representing all appcli commands.

Certain appcli commands cannot be run, or must be forced to run, when the
configuration directory is in specific states. This enum is used to represent
appcli commmands to allow the code to determine if the command can be run or
not.

For any appcli command that requires the configuration directory to be in
specific state to run, update this enum if the command is added, deleted, or
modified.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from enum import Enum, auto


class AppcliCommand(Enum):
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

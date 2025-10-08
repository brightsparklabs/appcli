#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles archiving and rotation of logs and files.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""


# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

# Standard imports.
from typing import Literal, List, Union
from enum import Enum
from pathlib import Path

# Vendor imports.
from pydantic import BaseModel

# Local imports.
from appcli.models.cli_context import CliContext
from appcli.logger import logger


# -----------------------------------------------------------------------------
# CLASSES
# -----------------------------------------------------------------------------


class CompressMode(str, Enum):
    """What type of action to perform when archiving."""

    APPEND = "append"
    """Add files to an existing archive (or create a new one)."""

    OVERWRITE = "overwrite"
    """Same as 'append' but deletes the file if it already exists."""

    CANCEL = "cancel"
    """Ignore if the archive file already exists."""


class CompressRule(BaseModel):
    """Rule to compress files into an archived file."""

    type: Literal["compress"] = "compress"
    """Explicitly declare rule type."""

    name: str
    """Name of the rule."""

    include_list: List[str] = ["[]"]
    """Glob pattern of files/dirs to include in the archive."""

    archive_file: Path
    """Archive to compress the files into."""

    mode: CompressMode = CompressMode.APPEND
    """How to operate when compressing the files."""


class PurgeRule(BaseModel):
    """Rule to purge files from the system."""

    type: Literal["purge"] = "purge"
    """Explicitly declare rule type."""

    name: str
    """Name of the rule."""

    include_list: List[str] = ["[]"]
    """Glob pattern of files/dirs to include in the purge."""


class CommandRule(BaseModel):
    """Rule for running commands in a container."""

    type: Literal["command"] = "command"
    """Explicitly declare rule type."""

    name: str
    """Name of the rule."""

    container: str
    """The container to run the command on."""

    command: str
    """The command string to execute."""


# Union object to allow subclassing of rules.
# NOTE: The order here matters. The first item in the list is the type used if
#       the discriminator field is not set in the data being deserialized.
#       If we were to explicitly specify a `discriminator`
#       (see https://stackoverflow.com/a/76449131/3602961), then we would
#       ALWAYS need to specify the type, so it would not default.
ArchiveRuleUnion = Union[CompressRule, PurgeRule, CommandRule]


class ArchiveRuleset(BaseModel):
    """Collection of archiving rules."""

    name: str
    """Name of the ruleset."""

    rules: List[ArchiveRuleUnion] = []
    """Rules that are part of this ruleset. Order matters for execution."""


class ArchiveManager:
    """
    Functions to implement archiving rules.
    """

    def __init__(self, cli_context: CliContext, archives: List = []):
        """Constructor."""
        self.cli_context: CliContext = cli_context
        self.archives: List[ArchiveRuleset] = []
        # NOTE: Convert to actual objects for validation and easy access.
        for ruleset in archives:
            self.archives.append(ArchiveRuleset.parse_obj(ruleset))

    def run_all_archive_rulesets(self):
        """Execute all archive rules."""
        if len(self.archives) == 0:
            logger.warn("No rules defined in the stack settings.")
        for rule in self.archives:
            self.run_archive_ruleset(rule.name)

    def run_archive_ruleset(self, ruleset_name: str):
        """Execute a set of archive rules.

        Args:
          archive_ruleset: Name of the ruleset to execute. Must be present in `self.archives`.
        """
        # Bail early if the ruleset does not exist or multiple rulesets with that name are found.
        matching_rulesets = [
            ruleset for ruleset in self.archives if ruleset.name == ruleset_name
        ]
        if len(matching_rulesets) == 0:
            raise KeyError(
                f"The archive rule `{ruleset_name}` was not found in the `stack-settings` file."
            )
        if len(matching_rulesets) > 1:
            raise KeyError(
                f"Multiple rules matching `{ruleset_name}` were found in the `stack-settings` file."
            )
        ruleset: ArchiveRuleset = matching_rulesets[0]
        logger.info(f"Executing the `{ruleset.name}` archive ruleset.")

        for rule in ruleset.rules:
            logger.info(f"Executing the `{ruleset.name}.{rule.name}` archiving rule.")

            # Need to determine what type of rule this is.
            if isinstance(rule, CompressRule):
                self._run_compress_rule(rule)
            elif isinstance(rule, PurgeRule):
                self._run_purge_rule(rule)
            elif isinstance(rule, CommandRule):
                self._run_command_rule(rule)
            else:
                raise NotImplementedError(
                    f"Rule `{rule.name}` is of type `{type(rule)}` which is not a vaild archive rule."
                )

    def _run_compress_rule(self, rule: CompressRule):
        """Execute a Compress archive rule."""
        pass

    def _run_purge_rule(self, rule: PurgeRule):
        """Execute a Purge archive rule."""
        pass

    def _run_command_rule(self, rule: CommandRule):
        """Execute a Command archive rule."""
        pass

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
from pathlib import Path
from datetime import datetime
import tarfile
import glob

# Vendor imports.
from pydantic import BaseModel

# Local imports.
from appcli.models.cli_context import CliContext
from appcli.logger import logger


# -----------------------------------------------------------------------------
# CLASSES
# -----------------------------------------------------------------------------


class CompressRule(BaseModel):
    """Rule to compress files into an archived file.
    This will overwrite any archive file that already exists.
    """

    type: Literal["compress"] = "compress"
    """Explicitly declare rule type."""

    name: str
    """Name of the rule."""

    include_list: List[str] = ["[]"]
    """Glob pattern of files/dirs in `data_dir` to include in the archive."""

    archive_file: str
    """Archive file in `data_dir` to compress the files into.
    Dateime is supported using the `%<value>` notation, i.e:

        archive_format: 'myapp_%m-%d-%Y.tar'

    Produces the file:

        data/myapp_06-05-2013.tar

    See: https://devhints.io/datetime
    NOTE: Because we support dynamic datetime this has to be a `str` and not `Path`.
    """


class PurgeRule(BaseModel):
    """Rule to purge files from the system."""

    type: Literal["purge"] = "purge"
    """Explicitly declare rule type."""

    name: str
    """Name of the rule."""

    include_list: List[str] = ["[]"]
    """Glob pattern of files/dirs to include in the purge."""


# Union object to allow subclassing of rules.
# NOTE: The order here matters. The first item in the list is the type used if
#       the discriminator field is not set in the data being deserialized.
#       If we were to explicitly specify a `discriminator`
#       (see https://stackoverflow.com/a/76449131/3602961), then we would
#       ALWAYS need to specify the type, so it would not default.
ArchiveRuleUnion = Union[CompressRule, PurgeRule]


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
            else:
                raise NotImplementedError(
                    f"Rule `{rule.name}` is of type `{type(rule)}` which is not a vaild archive rule."
                )

    def _run_compress_rule(self, rule: CompressRule):
        """Execute a Compress archive rule."""
        # Get the name of the archive.
        dated_archive_file = Path(datetime.now().strftime(rule.archive_file))
        archive_path = self.cli_context.data_dir / dated_archive_file

        # Remove the archive file if it already exists.
        if archive_path.exists():
            archive_path.unlink()

        # Write files to the archive.
        with tarfile.open(archive_path, "w:gz") as tar:
            for pattern in rule.include_list:
                # Glob search for all files that match the pattern.
                file_list = [
                    Path(p).resolve()
                    for p in glob.glob(str(self.cli_context.data_dir / pattern))
                ]
                for file in file_list:
                    tar.add(file, file.relative_to(self.cli_context.data_dir))
        logger.debug(f"Archive created at `{dated_archive_file}`.")

    def _run_purge_rule(self, rule: PurgeRule):
        """Execute a Purge archive rule."""
        # Determine which files need to be removed.
        full_file_list = []
        for pattern in rule.include_list:
            # Glob search for all files that match the pattern.
            file_list = [
                Path(p).resolve()
                for p in glob.glob(str(self.cli_context.data_dir / pattern))
            ]
            for file in file_list:
                full_file_list.append(file)

        # Unlink all the files.
        logger.debug(f"Removing the following files: `{full_file_list}`")
        for file in full_file_list:
            file.unlink()

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
import datetime
import tarfile
import glob
import os

# Vendor imports.
from pydantic import BaseModel, Field, field_validator

# Local imports.
from appcli.models.cli_context import CliContext
from appcli.logger import logger


# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------


# NOTE: This would ideally be a method of the `CompressRule` class.
# However we cannot do that because it needs to be callable by `default_factory`,
# which does not have scope over the `CompressRule` class.
# Instead we have a function in that class which is a proxy to this one.
def resolve_archive_filename(string: str = "%Y-%m%d_${APP_NAME}.tgz") -> str:
    """Take the provided archive filename and resolve all the datetime format strings and environment variables."""
    resolved_string = os.path.expandvars(string)
    resolved_string = datetime.datetime.now().strftime(resolved_string)
    return resolved_string


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

    # This is a little bit confusing so I'm going to try and explain what is going on here.
    # The `archive_file` field can contain Datestrings or Environment vars which need to be templated out during instantiation, e.g.
    #
    #  "%Y-%m%d_${APP_NAME}.tgz"  ->  "2013-0605_myapp.tgz"
    #
    # We use the pydantic `field_validator` to do this, but that does NOT work when a default value is being used.
    #
    #  archive_file: str = "%Y-%m%d_${APP_NAME}.tgz"  # Will not get templated.
    #
    # To ensure this default is also templated we use a `default_factory` which points to a global function.
    # That global function is what stores the default, which is why you do not see it here.
    # We also proxy the `field_validator` function to the global function to ensure consistency.
    #
    # TLDR; this ensures that whether a value is supplied here or not, it will always be templated.
    archive_file: str = Field(default_factory=resolve_archive_filename)
    """Archive file in `data_dir` to compress the files into.
    Datetime is supported using the `%<value>` notation.
    Environment variables are supported using the `${<value>}` notation.

        archive_format: '%Y-%m%d_${APP_NAME}.tgz'

    Produces the file:

        data/2013-0605_myapp.tgz

    See: https://devhints.io/datetime
    NOTE: Because we support dynamic datetime and env vars, this has to be a `str` and not `Path`.
    """

    # NOTE: This is essentially just a proxy to the global `resolve_archive_filename` function, which allows it to be called by pydantic.
    @field_validator("archive_file", mode="before")
    @classmethod
    def resolve_archive_filename(cls, v: str) -> str:
        """Take the provided archive filename and resolve all the datetime format strings and environment variables."""
        return resolve_archive_filename(v)


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
            self.archives.append(ArchiveRuleset.model_validate(ruleset))

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
                # NOTE: Because pydantic does validation we should not get here.
                # If this gets triggered, you (the developer) have defined a new `ArchiveRule` without implementing it.
                # Please fill out the new `elif` branch and corresponding function to resolve.
                raise NotImplementedError(
                    f"Rule `{rule.name}` is of type `{type(rule)}` which has not been implemented."
                )

    def _run_compress_rule(self, rule: CompressRule):
        """Execute a Compress archive rule."""
        # Get the path of the archive.
        archive_path = self.cli_context.data_dir / rule.archive_file

        # Remove the archive file if it already exists.
        if archive_path.exists():
            try:
                archive_path.unlink()
            except OSError as ex:
                logger.error(
                    f"Unable to remove `{archive_path}`. Check file permissions and that not other process has it locked."
                )
                raise ex
        archive_path.parent.mkdir(parents=True, exist_ok=True)

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
        logger.debug(f"Archive created at `{rule.archive_file}`.")

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
            try:
                file.unlink()
            except OSError as ex:
                logger.error(
                    f"Unable to remove `{file}`. Check file permissions and that not other process has it locked."
                )
                raise ex

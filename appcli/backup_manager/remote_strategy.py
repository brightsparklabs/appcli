#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Remote backup strategy classes.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import os
import time
import urllib.parse
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import Optional

# vendor libraries
import boto3
from botocore.exceptions import ClientError
from dataclasses_json import dataclass_json
from tabulate import tabulate

# local libraries
from appcli.crypto.cipher import Cipher
from appcli.logger import logger

# ------------------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------------------


class RemoteBackupStrategy:
    """ Base class for all remote strategies. """

    def backup(self, backup_filename: Path, key_file: Path):
        """
        Backup method for the remote strategy. Must be overwritten.

        Args:
            backup_filename: (str). The name of the backup to restore from. This lives in the backup folder.
            key_file: (Path). The path to the key file.
        """
        raise NotImplementedError(
            "The backup method has not been overwritten by the derived strategy class."
        )


@dataclass_json
@dataclass
class RemoteBackup:
    """
    A dataclass that represents the common tags that all remote backup strategies have.

    """

    strategy_type: str = field(default="")
    """ The remote backup strategy type. This must match a key in remote_strategy_factory.py STRATEGIES. """
    name: Optional[str] = field(default="")
    """ An optional name/description for the remote strategy. """
    configuration: dict = field(default_factory=dict)
    """ A dict that contains additional configuration values that allows the remote strategy to run. """
    strategy: RemoteBackupStrategy = field(init=False)
    """ The remote backup strategy implementation """

    def __post_init__(self):
        """Called after __init__()."""

        # None of the fields should be set `None` - if any are, override with the default.
        for f in fields(self):

            # Skip fields that are intentionally not initialised by __init__()
            if f.init is False:
                continue

            val = getattr(self, f.name)
            if val is None:
                # If the field is 'empty' and set to None in the settings, default to:
                # - f.default if it's defined, otherwise
                # - f.default_factory() if f.default_factory is defined, otherwise
                # - None (as there's no other reasonable default).
                default_value = None
                if f.default != MISSING:
                    default_value = f.default
                elif f.default_factory != MISSING:
                    default_value = f.default_factory()

                logger.debug(
                    f"Overriding 'None' for [{f.name}] with default [{default_value}]"
                )
                setattr(self, f.name, default_value)

        # Instantiate the strategy
        self.strategy = RemoteStrategyFactory.get_strategy(
            self.strategy_type, self.configuration
        )

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------
    def backup(self, backup_filename: Path, key_file: Path):
        """
        Call the set strategies backup method

        Args:
            backup_filename: str. The full Path of the backup to restore from. This lives in the backup folder.
            key_file: Path. The path to the key file.
        """
        logger.info(f"Initiating backup [{self.name}]")
        self.strategy.backup(backup_filename, key_file)


@dataclass_json
@dataclass
class AwsS3Strategy(RemoteBackupStrategy):
    """
    A dataclass that represents a Remote backup strategy for pushing a backup to an S3 bucket.
    Implements RemoteBackupStrategy.
    """

    access_key: str
    """ The AWS access key. """
    secret_key: str
    """ The AWS secret key, encrypted with appcli 'encrypt' command. """
    bucket_name: str
    """ The name of the S3 bucket to upload the backup to. """
    bucket_path: Optional[str] = ""
    """ An optional AWS bucket path to use when uploading a backup. """
    tags: Optional[dict] = field(default_factory=dict)
    """ An optional dict of tags to add to the backup in S3. """

    # --------------------------------------------------------------------------
    # OVERRIDE: RemoteBackupStrategy
    # --------------------------------------------------------------------------

    def backup(self, backup_filename: Path, key_file: Path):
        """
        Backup method for an S3 remote strategy.

        Args:
            backup_filename: (str). The name of the backup to restore from. This lives in the backup folder.
            key_file: (Path). The path to the key file.

        Throws:
            Exception (of varying types):
                Failed to decrypt the secret_key.
                Failed to upload the backup with boto.
        """
        # Decrypt our secret key.
        cipher = Cipher(key_file)
        try:
            decrypted_secret_key = cipher.decrypt(self.secret_key)
        except ValueError as e:
            raise ValueError(
                "Could not decrypt 'secret_key' - must be encrypted with 'encrypt' command."
            ) from e

        # Table of configuration variables to print
        table = [
            ["Backup file", backup_filename],
            [
                "Bucket Name",
                f"{self.bucket_name}",
            ],
            ["Bucket access_key", f"{self.access_key}"],
            ["Bucket path", f"{self.bucket_path}"],
            ["tags", f"{self.tags}"],
        ]

        logger.info(
            tabulate(table, colalign=("right",)),
        )

        s3 = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=decrypted_secret_key,
        )
        try:
            # rstrip("/") the bucket path so we don't get nested into a folder called '/'
            s3.upload_file(
                backup_filename,
                self.bucket_name,
                self.bucket_path.rstrip("/") + "/" + os.path.basename(backup_filename),
                # `Tagging` accepts a url like encoded string of tags.
                # i.e "key1=value1&key2=value2&..."
                ExtraArgs={"Tagging": urllib.parse.urlencode(self.tags)},
            )
        except ClientError as e:
            # Wrap the ClientError with the bucket name.
            raise ClientError(
                f"Failed to upload backup to bucket {self.bucket_name} - {e}"
            ) from e


class RemoteStrategyFactory:
    """
    Factory for getting all remote strategies that match the config
    """

    STRATEGIES = {"S3": AwsS3Strategy}
    """ A dict of remote strategy classes that are implemented. """

    @staticmethod
    def get_strategy(remote_type: str, configuration: dict) -> RemoteBackupStrategy:
        """
        Get an instance of a remote strategy for a given remote strategy type.

        Args:
            remote_type: (str). The type of strategy to build.
            configuration: (dict). The extra configuration values to use in building the strategy.

        Returns:
            [RemoteBackupStrategy]: An instance of a strategy class.

        """

        # Get the strategy class for the specified type.
        strategy_class = RemoteStrategyFactory.STRATEGIES.get(remote_type, None)

        if strategy_class is None:
            raise TypeError(
                f"No remote backup strategies found for type [{remote_type}]"
            )

        # Instantiate the strategy class and return that instance.
        return strategy_class.from_dict(configuration)

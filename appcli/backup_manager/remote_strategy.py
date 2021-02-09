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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# vendor libraries
import boto3
import cronex
from botocore.exceptions import ClientError
from dataclasses_json import dataclass_json
from tabulate import tabulate

# local libraries
from appcli.crypto.cipher import Cipher
from appcli.logger import logger

# from appcli.backup_manager.remote_strategy_factory import RemoteStrategyFactory


@dataclass_json
@dataclass
class RemoteBackup:
    """
    A dataclass that represents the common tags that all remote backup strategies have.

    """

    strategy_type: str
    """ The remote backup strategy type. This must match a key in remote_strategy_factory.py STRATEGIES. """
    name: Optional[str] = ""
    """ An optional name/description for the remote strategy. """
    frequency: Optional[str] = "* * *"
    """ An optional CRON frequency with the time stripped out i.e. `* * *` for specifying when this strategy should run. """
    configuration: Optional[dict] = field(default_factory=dict)
    """ An optional dict that contains additional configuration values that allows the remote strategy to run. """

    # def __post_init__(self):
    # calls remote_strategy_factory
    #    self.strategy = RemoteStrategyFactory.get_strategy(self.strategy_type, self.configuration)

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
        self.strategy.backup(backup_filename, key_file)

    def should_run(self) -> bool:
        """
        Verify if the backup strategy should run based on todays date and the frequency value set.

        Returns:
            True if the frequency matches today, False if it does not.
        """

        # Our configuration is just the last 3 values of a cron pattern, prepend hour/minute as wild-cards.
        frequency = f"* * {self.frequency}"
        try:
            job = cronex.CronExpression(frequency)
        except ValueError as e:
            logger.error(
                f"Frequency for remote strategy [{self.name}] is not valid [{self.frequency}]. [{e}]"
            )
            return False

        return job.check_trigger(time.gmtime(time.time())[:5])


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
class AwsS3Strategy(RemoteBackupStrategy):
    """
    A dataclass that represents a Remote backup strategy for pushing a backup to an S3 bucket.
    Implements RemoteBackupStrategy.
    """

    access_key: str
    """ The AWS access key. """
    secret_key: str
    """ The AWS secret key. """
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
        secret_key = cipher.decrypt(self.secret_key)

        # Table of configuration variables to print
        table = [
            ["Initiating the S3 backup", f"{self.name}"],
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
            aws_secret_access_key=secret_key,
        )
        try:
            s3.upload_file(
                backup_filename,
                self.bucket_name,
                self.bucket_path + "/" + os.path.basename(backup_filename),
                # `Tagging` accepts a url like encoded string of tags.
                # i.e "key1=value1&key2=value2&..."
                ExtraArgs={"Tagging": urllib.parse.urlencode(self.tags)},
            )
        except ClientError as e:
            # Wrap the ClientError with the bucket name.
            raise ClientError(
                f"Failed to upload backup to bucket {self.bucket_name} - {e}"
            )

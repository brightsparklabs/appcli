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
    """"""

    strategy_type: str
    name: Optional[str] = ""
    frequency: Optional[str] = "* * *"
    configuration: Optional[dict] = field(default_factory=dict)
    # key_file: field(default_factory=Path)

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------
    def backup(self, backup_filename, key_file):
        self.strategy.backup(backup_filename, key_file)

    # def __post_init__(self):
    # calls remote_strategy_factory
    #    self.strategy = RemoteStrategyFactory.get_strategy(self.strategy_type, self.configuration)

    def should_run(self):

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
    def backup(self, backup_filename: Path, key_file: Path):
        raise NotImplementedError(
            "The backup method has not been overridden by the derived strategy class."
        )


@dataclass_json
@dataclass
class AwsS3Strategy(RemoteBackupStrategy):
    """
    Remote backup strategy for pushing a backup to an S3 bucket.
    Implements RemoteBackupStrategy.
    """

    access_key: str
    secret_key: str
    bucket_name: str
    bucket_path: Optional[str] = ""
    tags: Optional[dict] = field(default_factory=dict)

    # --------------------------------------------------------------------------
    # OVERRIDE: RemoteBackupStrategy
    # --------------------------------------------------------------------------

    def backup(self, backup_filename: Path, key_file: Path):

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

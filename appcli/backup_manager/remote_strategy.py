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
import urllib.parse
from pathlib import Path

# vendor libraries
import boto3
from botocore.exceptions import ClientError

#from appcli.crypto.cipher import Cipher

# local libraries
from appcli.logger import logger


class RemoteStrategy:
    """
    Base class for a remote backup strategy.
    """

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------
    def __init__(self, conf, key_file: Path):
        self.name = conf["name"]
        self.type = conf["type"]
        self.frequency = conf["frequency"]
        self.configuration = conf["configuration"]
        self.key_file = key_file

    # ------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------------------
    def backup(self, backup_filename):
        pass


class AwsS3Strategy(RemoteStrategy):
    """
    Remote backup strategy for pushing a backup to an S3 bucket.
    Implements RemoteStrategy.
    """

    # --------------------------------------------------------------------------
    # CONSTRUCTOR
    # --------------------------------------------------------------------------
    def __init__(self, conf, key_file: Path):
        super().__init__(conf, key_file)

        # cipher = Cipher(self.key_file)

        self.s3_bucket = self.configuration["bucket_name"]
        # self.s3_access_key = cipher.decrypt(self.configuration['access_key'])
        # self.s3_secret_key = cipher.decrypt(self.configuration['secret_key'])
        # giving invalid mac
        #  File "/usr/local/lib/python3.8/site-packages/Crypto/Cipher/_mode_gcm.py", line 508, in verify
        #   raise ValueError("MAC check failed")
        # ValueError: MAC check failed

        self.s3_access_key = self.configuration["access_key"]
        self.s3_secret_key = self.configuration["secret_key"]
        self.s3_bucket_path = self.configuration["s3_bucket_path"]
        self.s3_tags = self.configuration["tags"]

    # --------------------------------------------------------------------------
    # OVERRIDE: RemoteStrategy
    # --------------------------------------------------------------------------

    def backup(self, backup_filename):
        logger.info(f"Initiating the S3 backup '{self.name}'.")
        logger.info(f"Bucket Name '{self.s3_bucket}'.")
        logger.info(f"Bucket access_key '{self.s3_access_key}'.")
        logger.info(f"Bucket path '{self.s3_bucket_path}'.")

        s3 = boto3.client(
            "s3",
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
        )
        try:
            s3.upload_file(
                backup_filename,
                self.s3_bucket,
                self.s3_bucket_path + "/" + os.path.basename(backup_filename),
                # `Tagging` accepts a url like encoded string of tags.
                # i.e "key1=value1&key2=value2&..."
                ExtraArgs={"Tagging": urllib.parse.urlencode(self.s3_tags)},
            )
        except ClientError as e:
            logger.error(f"Failed to upload backup to bucket {self.s3_bucket} - {e}")

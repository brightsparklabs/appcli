#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# standard libraries
import os

# local libraries
from appcli.logger import logger

# vendor libraries
import boto3
from botocore.exceptions import ClientError


class RemoteStrategy:
    def __init__(self, conf):
        print(conf)
        self.name = conf['name']
        self.type = conf['type']
        self.frequency = conf['frequency']
        self.configuration = conf['configuration']

    def backup():
        pass
    
class AwsS3Strategy(RemoteStrategy):
    def __init__(self, conf):
        super().__init__(conf)
        self.s3_bucket = self.configuration['bucket_name']
        self.s3_access_key = self.configuration['access_key']
        self.s3_secret_key = self.configuration['secret_key']
        self.s3_bucket_path = self.configuration['s3_bucket_path']
        self.s3_tags = self.configuration['tags']

    def backup(self, backup_filename):
        logger.info(f"Initiating the S3 backup '{self.name}'.")
        logger.info(f"Bucket Name '{self.s3_bucket}'.")
        logger.info(f"Bucket access_key '{self.s3_access_key}'.")
        logger.info(f"Bucket path '{self.s3_bucket_path}'.")

        
        s3 = boto3.client('s3', aws_access_key_id=self.s3_access_key, aws_secret_access_key=self.s3_secret_key)
        try:
            response = s3.upload_file(backup_filename, 
            self.s3_bucket, 
            self.s3_bucket_path + "/" + os.path.basename(backup_filename))
        except ClientError as e:
            logger.error(f"Failed to upload backup to bucket {self.s3_bucket} - {e}")
        

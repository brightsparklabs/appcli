#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for the backup manager.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from typing import Dict, List

from appcli.backup_manager.backup_manager import BackupManager

# local libraries
from appcli.backup_manager.remote_strategy import (
    AwsS3Strategy,
    RemoteBackup,
    RemoteBackupStrategy,
)

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_simple_parsing():

    remotes = [
        create_remote_definition(
            name="s3_test",
            strategy="S3",
            frequency="* * *",
            configuration=create_S3_configuration(),
        )
    ]

    # test_backup_configuration = create_backup_configuration(3, ["ignore_me"], remotes)


# backup_manager: BackupManager = BackupManager.from_dict(test_backup_configuration)

# assert backup_manager.backup_limit == test_backup_configuration["backup_limit"]
# assert backup_manager.ignore_list == test_backup_configuration["ignore_list"]
#  assert len(backup_manager.remote) == 1

# remote_backups = backup_manager.get_remote_backups()
# assert len(remote_backups) == 1

# remote_backup: RemoteBackup = remote_backups[0]
# basic_remote = test_backup_configuration["remote"][0]
# assert remote_backup.name == basic_remote["name"]
# assert remote_backup.strategy_type == basic_remote["strategy_type"]
# assert remote_backup.frequency == basic_remote["frequency"]

# remote_strategy: RemoteBackupStrategy = remote_backup.strategy
# basic_remote_strategy = basic_remote["configuration"]
# assert isinstance(remote_strategy, AwsS3Strategy)
# assert remote_strategy.bucket_name == basic_remote_strategy["bucket_name"]
# assert remote_strategy.access_key == basic_remote_strategy["access_key"]
# assert remote_strategy.secret_key == basic_remote_strategy["secret_key"]
# assert remote_strategy.bucket_path == basic_remote_strategy["bucket_path"]
# assert remote_strategy.tags == basic_remote_strategy["tags"]


# TODO: Add more complex test cases

# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


# def create_backup_configuration(
#    backup_limit: int = 0, ignore_list: List[str] = [], remote: List[dict] = []
# ):
#    return {"backup_limit": backup_limit, "ignore_list": ignore_list, "remote": remote}


def create_remote_definition(
    name: str, strategy: str, configuration: dict, frequency: str = "* * *"
) -> Dict:
    return {
        "name": name,
        "strategy_type": strategy,
        "frequency": frequency,
        "configuration": configuration,
    }


def create_S3_configuration(
    bucket_name: str = "test-bucket-name",
    access_key: str = "test-access-key",
    secret_key: str = "test-secret-key",
    bucket_path: str = "bucket-directory/",
    tags: dict = {},
):
    return {
        "bucket_name": bucket_name,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket_path": bucket_path,
        "tags": tags,
    }

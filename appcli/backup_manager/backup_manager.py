#!/usr/bin/env python3
# # -*- coding: utf-8 -*-


# local libraries
from appcli.backup_manager.remote_strategy import AwsS3Strategy



class RemoteStrategyFactory:


    @staticmethod
    def get_strategy(backup_config):
        strategies = {
            "S3": AwsS3Strategy
        }


        #double check backup_config is a dictionary

        backups_to_keep = backup_config['numberOfBackupsToKeep']
        ignore_list = backup_config['ignoreList']
        backups = backup_config['remote']

        

        backup_strategies = []

        for backup in backups:
            cl = strategies.get(backup['type'], lambda: "Invalid remote strategy")
            cl(backup)
            
            backup_strategies.append(cl(backup))

        return backup_strategies

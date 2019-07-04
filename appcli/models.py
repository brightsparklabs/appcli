#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

from types import LambdaType
from typing import NamedTuple, List

class ConfigSetting(NamedTuple):
    path: str
    message: str
    validate: LambdaType = lambda _, x: True

class ConfigSettingsGroup(NamedTuple):
    title: str
    settings: List[ConfigSetting]

class ConfigCli(NamedTuple):
    settings_groups: List[ConfigSettingsGroup]

class Configuration(NamedTuple):
    app_name: str
    config_cli: ConfigCli

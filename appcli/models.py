#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

from typing import NamedTuple

class Configuration(NamedTuple):
    app_name: str
    app_root_dir: str
    host_root_dir: str = "/"
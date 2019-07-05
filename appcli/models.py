#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

from pathlib import Path
from typing import NamedTuple

class Configuration(NamedTuple):
    app_name: str
    docker_compose_file: Path

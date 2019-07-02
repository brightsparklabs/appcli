#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Default package.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# internal libraries
from .appcli import AppCli, Configuration

def create_cli(configuration: Configuration):
    app = AppCli(configuration)
    return app.cli

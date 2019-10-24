#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Python Package File
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# always prefer setuptools over distutils
from setuptools import setup, find_packages
# to use a consistent encoding
from codecs import open
from os import path
from subprocess import run, PIPE

# ------------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------------------

def get_version():
    try:
        process = run(["git", "describe", "--dirty", "--always"], stdout=PIPE)
        line = process.stdout.strip().decode('utf-8')
        return line
    except Exception as ex:
        return 'UNKNOWN'

# ------------------------------------------------------------------------------
# SETUP DEFINITION
# ------------------------------------------------------------------------------

here = path.dirname(path.realpath(__file__))
# get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# get the license
with open(path.join(here, 'LICENSE'), encoding='utf-8') as f:
    license = f.read()

setup(
    name="appcli",
    version=get_version(),
    description=long_description,
    license=license,
    author='brightSPARK Labs',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'click',
        'coloredlogs',
        'inquirer',
        'jinja2',
        'python-dotenv',
        'python-keycloak',
        'ruamel-yaml'
    ]
)


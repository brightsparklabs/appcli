#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Python Package File
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# to use a consistent encoding
from codecs import open
from os import path
from subprocess import PIPE, run

# always prefer setuptools over distutils
from setuptools import find_packages, setup

# ------------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------------------


def get_version():
    try:
        process = run(["git", "describe", "--dirty", "--always"], stdout=PIPE)
        line = process.stdout.strip().decode("utf-8")
        return line
    except Exception as ex:
        return "UNKNOWN"


# ------------------------------------------------------------------------------
# SETUP DEFINITION
# ------------------------------------------------------------------------------

here = path.dirname(path.realpath(__file__))
# get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# get the license
with open(path.join(here, "LICENSE"), encoding="utf-8") as f:
    license = f.read()

setup(
    name="appcli",
    version=get_version(),
    description=long_description,
    license=license,
    author="brightSPARK Labs",
    author_email="enquire@brightsparklabs.com",
    url="www.brightsparklabs.com",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    include_package_data=True,
    install_requires=[
        "click==7.1.2",
        "coloredlogs==14.0",
        "GitPython==3.1.12",
        "jinja2==2.11.2",
        "python-dotenv==0.14.0",
        "python-keycloak==0.22.0",
        "pycryptodome==3.9.8",
        "ruamel-yaml==0.16.10",
        "tabulate==0.8.7",
    ],
    extras_require={"dev": ["black", "flake8", "isort", "pytest"]},
)

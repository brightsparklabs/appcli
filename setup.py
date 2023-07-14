#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Python Package File
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

import re

# to use a consistent encoding
from codecs import open
from os import path
from subprocess import PIPE, run

# always prefer setuptools over distutils
from setuptools import find_namespace_packages, setup

# ------------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------------------


def get_version():
    try:
        process = run(["git", "describe", "--dirty", "--always"], stdout=PIPE)
        line = process.stdout.strip().decode("utf-8")
        # Needs to be PEP 440 compliant.
        compliant_version = re.sub("-.*", "", line)
        return compliant_version
    except Exception:
        return "UNKNOWN"


# ------------------------------------------------------------------------------
# SETUP DEFINITION
# ------------------------------------------------------------------------------

here = path.dirname(path.realpath(__file__))
# get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="bsl-appcli",
    version=get_version(),
    description="A library for adding CLI interfaces to applications in the brightSPARK Labs style",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT License",
    author="brightSPARK Labs",
    author_email="enquire@brightsparklabs.com",
    url="https://www.brightsparklabs.com",
    packages=find_namespace_packages(exclude=["contrib", "docs", "tests"]),
    include_package_data=True,
    install_requires=[
        "boto3==1.26.165",
        "click==8.1.3",
        "coloredlogs==15.0.1",
        "cronex==0.1.3.1",
        "dataclasses-json==0.5.7",
        "deepdiff==6.3.0",
        "GitPython==3.1.31",
        "jinja2==3.1.2",
        "pre-commit==3.3.3",
        "pycryptodome==3.18.0",
        "pydantic==2.0.1",
        "pyfiglet==0.8.post1",
        "python-keycloak==0.22.0",
        "python-slugify==8.0.1",
        "ruamel-yaml==0.17.32",
        "tabulate==0.9.0",
        "wheel==0.40.0",
    ],
    extras_require={"dev": ["black", "flake8", "isort", "pytest"]},
)

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
from setuptools import find_namespace_packages, setup

# ------------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------------------


def get_version():
    try:
        process = run(["git", "describe", "--dirty", "--always"], stdout=PIPE)
        line = process.stdout.strip().decode("utf-8")
        return line
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
        "boto3==1.26.41",
        "click==8.1.3",
        "coloredlogs==15.0.1",
        "cronex==0.1.3.1",
        "dataclasses-json==0.5.7",
        "deepdiff==6.2.3",
        "GitPython==3.1.30",
        "jinja2==3.1.2",
        "pre-commit==3.0.4",
        "pycryptodome==3.17",
        "pydantic==1.10.4",
        "python-keycloak==0.22.0",
        "python-slugify==8.0.0",
        "ruamel-yaml==0.17.21",
        "tabulate==0.9.0",
        "wheel==0.38.4",
    ],
    extras_require={"dev": ["black", "flake8", "isort", "pytest"]},
)

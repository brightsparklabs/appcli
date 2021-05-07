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
        "boto3==1.17.17",
        "click==7.1.2",
        "coloredlogs==15.0",
        "cronex==0.1.3.1",
        "dataclasses-json==0.5.2",
        "deepdiff==5.3.0",
        "GitPython==3.1.14",
        "jinja2==2.11.3",
        "pycryptodome==3.10.1",
        "python-dotenv==0.17.0",
        "python-keycloak==0.22.0",
        "python-slugify==4.0.1",
        "ruamel-yaml==0.16.12",
        "tabulate==0.8.9",
        "wheel==0.36.2",
    ],
    extras_require={"dev": ["black", "flake8", "isort", "pytest"]},
)

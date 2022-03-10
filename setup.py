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

# always prefer setuptools over distutils
from setuptools import find_namespace_packages, setup
from dunamai import Version

# ------------------------------------------------------------------------------
# SETUP DEFINITION
# ------------------------------------------------------------------------------

# Custom version pattern for dunamai.
# Copied from dunamai's __init__.py, and removed the `v` prefix since we don't use it on our tags.
_VERSION_PATTERN = r"""
    (?x)                                                        (?# ignore whitespace)
    ^((?P<epoch>\d+)!)?(?P<base>\d+(\.\d+)*)                   (?# v1.2.3 or v1!2000.1.2)
    ([-._]?((?P<stage>[a-zA-Z]+)[-._]?(?P<revision>\d+)?))?     (?# b0)
    (\+(?P<tagged_metadata>.+))?$                               (?# +linux)
""".strip()

# ------------------------------------------------------------------------------
# SETUP DEFINITION
# ------------------------------------------------------------------------------

here = path.dirname(path.realpath(__file__))
# get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="bsl-appcli",
    version=Version.from_any_vcs(pattern=_VERSION_PATTERN).serialize(format="{base}+{distance}.{commit}"),
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
        "boto3==1.21.8",
        "click==8.0.4",
        "coloredlogs==15.0.1",
        "cronex==0.1.3.1",
        "dataclasses-json==0.5.6",
        "deepdiff==5.7.0",
        "GitPython==3.1.27",
        "jinja2==3.0.3",
        "pycryptodome==3.14.1",
        "pydantic==1.9.0",
        "python-keycloak==0.22.0",
        "python-slugify==6.0.1",
        "ruamel-yaml==0.17.21",
        "tabulate==0.8.9",
        "wheel==0.37.1",
    ],
    extras_require={"dev": ["black", "flake8", "isort", "pytest"]},
)

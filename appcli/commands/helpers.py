#!/usr/bin/env python3
# # -*- coding: utf-8 -*-


# standard library
from pathlib import Path

# vendor libraries
import click

# local libraries
from appcli.crypto import crypto
from appcli.crypto.cipher import Cipher
from appcli.logger import logger


# encrypt helper function
def encrypt_helper(cli_context, text):
    key_file: Path = cli_context.get_key_file()
    if not key_file.is_file():
        logger.info("Creating encryption key at [%s]", key_file)
        crypto.create_and_save_key(key_file)

    cipher = Cipher(key_file)
    if text is None:
        result = cipher.encrypt(
            click.prompt("Please enter string to be encrypted", type=str)
        )
    else:
        result = cipher.encrypt(text)
    return result

#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles encryption/decryption of data.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import re
from pathlib import Path

# vendor libraries
from Crypto.Random import get_random_bytes

# local libraries
from appcli.crypto.cipher import Cipher
from appcli.logger import logger


def create_key() -> bytes:
    return get_random_bytes(32)


def create_and_save_key(key_file: Path):
    if key_file.exists():
        raise FileExistsError(
            f"Cannot create keyfile at [{key_file.absolute().as_posix()}] as a file already exists at this path."
        )
    logger.debug("Creating key file at [%s]", key_file)
    key_file.write_bytes(create_key())


def decrypt_values_in_file(encrypted_file: Path, decrypted_file: Path, key_file: Path):
    cipher = Cipher(key_file)
    regex = "enc:[^:]+:[^:]+:end"
    cache = {}

    replaced_lines = []
    with encrypted_file.open(mode="r") as input:
        for line in input:
            encrypted_strings = set(re.findall(regex, line))
            replaced_line = line
            for encrypted_string in encrypted_strings:
                decrypted_string = None
                if encrypted_string in cache:
                    decrypted_string = cache[encrypted_string]
                else:
                    decrypted_string = cipher.decrypt(encrypted_string)
                    cache[encrypted_string] = decrypted_string

                replaced_line = replaced_line.replace(
                    encrypted_string, decrypted_string
                )

            replaced_lines.append(replaced_line)

    decrypted_file.write_text("".join(replaced_lines))


def decrypt_value(encrypted_value: str, key_file: Path):
    """Decrypts a given input value. If the value is unencrypted, will return
    it verbatim.
    """

    if not isinstance(encrypted_value, str):
        logger.debug(f"Did not decrypt non-string value [{encrypted_value}].")
        return encrypted_value

    regex = "^enc:[^:]+:[^:]+:end$"
    if re.match(regex, encrypted_value) is None:
        logger.debug(f"Did not decrypt unencrypted value [{encrypted_value}].")
        return encrypted_value

    cipher = Cipher(key_file)
    return cipher.decrypt(encrypted_value)

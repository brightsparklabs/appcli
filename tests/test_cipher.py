#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for cipher.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# vendor libraries
import pytest
from pathlib import Path

# local libraries
from appcli.crypto import crypto
from appcli.crypto.cipher import Cipher


def test_aes_gcm(tmpdir):
    key_file = Path(tmpdir, "key")
    print(f"key_file: ${key_file}")
    crypto.create_and_save_key(key_file)
    cipher = Cipher(key_file)

    plaintext = "a message to encrypt"
    ciphertext = cipher.encrypt(plaintext)
    print(f"ciphertext: {ciphertext}")
    assert ciphertext != plaintext
    result = cipher.decrypt(ciphertext)
    assert result == plaintext

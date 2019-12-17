#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for cipher.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from pathlib import Path

# vendor libraries
import pytest

# local libraries
from appcli.crypto import crypto
from appcli.crypto.cipher import Cipher

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def test_aes_gcm(tmpdir):
    cipher = create_cipher(tmpdir)

    plaintext = "a message to encrypt"
    ciphertext = cipher.encrypt(plaintext)
    assert ciphertext != plaintext
    result = cipher.decrypt(ciphertext)
    assert result == plaintext


def test_missing_prefix(tmpdir):
    cipher = create_cipher(tmpdir)
    with pytest.raises(Exception) as ex:
        cipher.decrypt(":id=aes-gcm:data:end")
    assert "Encrypted data must have format [enc:<metadata>:<data>:end]" in str(
        ex.value
    )


def test_missing_suffix(tmpdir):
    cipher = create_cipher(tmpdir)
    with pytest.raises(Exception) as ex:
        cipher.decrypt("enc:id=aes-gcm:data:")
    assert "Encrypted data must have format [enc:<metadata>:<data>:end]" in str(
        ex.value
    )


def test_invalid_id(tmpdir):
    cipher = create_cipher(tmpdir)
    with pytest.raises(Exception) as ex:
        cipher.decrypt("enc:id=invalid:data:end")
    assert "Attempted to use wrong cipher" in str(ex.value)


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------


def create_cipher(tmpdir) -> Cipher:
    key_file = Path(tmpdir, "key")
    crypto.create_and_save_key(key_file)
    return Cipher(key_file)

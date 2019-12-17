#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Unit tests for crypto.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
from pathlib import Path

# local libraries
from appcli.crypto import crypto
from appcli.crypto.cipher import Cipher


def test_decrypt_values_in_file(tmpdir):
    key_file = Path(tmpdir, "key")
    crypto.create_and_save_key(key_file)
    cipher = Cipher(key_file)

    lines = [
        "a message to encrypt",
        "another message",
        "a repeated message",
    ]
    encrypted_lines = [cipher.encrypt(x) for x in lines]

    encrypted_file_text = f"""
        normal text
        {encrypted_lines[0]}
        {encrypted_lines[1]}
        {encrypted_lines[2]}
        {encrypted_lines[0]}:{encrypted_lines[1]}
        {encrypted_lines[0]}::{encrypted_lines[1]}@{encrypted_lines[2]}
        {encrypted_lines[0]}:{encrypted_lines[1]}enc:::end{encrypted_lines[2]}
    """
    expected_decrypted_text = f"""
        normal text
        {lines[0]}
        {lines[1]}
        {lines[2]}
        {lines[0]}:{lines[1]}
        {lines[0]}::{lines[1]}@{lines[2]}
        {lines[0]}:{lines[1]}enc:::end{lines[2]}
    """

    encrypted_file = Path(tmpdir, "encrypted")
    encrypted_file.write_text(encrypted_file_text)

    decrypted_file = Path(tmpdir, "decrypted")
    crypto.decrypt_values_in_file(encrypted_file, decrypted_file, key_file)
    decrypted_text = decrypted_file.read_text()

    assert expected_decrypted_text == decrypted_text

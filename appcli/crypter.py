#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

"""
Handles encryption/decryption of data.
________________________________________________________________________________

Created by brightSPARK Labs
www.brightsparklabs.com
"""

# standard libraries
import json
from base64 import b64encode, b64decode
from pathlib import Path

# vendor libraries
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def create_key() -> bytes:
    return get_random_bytes(32)


def create_and_save_key(key_file: Path):
    key_file.write_bytes(create_key())


class Cipher:
    """
    Factory for getting a Cipher.
    """

    def __init__(self, key_file: Path, cipherId="aes-gcm"):
        """
        Args:
            key_file: Path. Key file to use for encryption/decryption.
            cipherId: str. Identifier of the cipher to use.
        """

        self.cipherId = cipherId
        # TODO: when we support more ciphers, then use a look up instead
        cipherClass = AesGcmCipher
        self.cipher = cipherClass(key_file)

    def encrypt(self, data: str) -> str:
        """
        Encrypts the specified data with this cipher.

        Args:
            data: str. Data to encrypt.
        Returns:
            the resulting ciphertext as a string.
        """
        data_bytes = data.encode("utf-8")
        result = self.cipher.encrypt(data_bytes)
        return f"enc:{self.cipherId}:{result}:"

    def decrypt(self, data: str) -> str:
        """
        Decrypts the specified data with this cipher.

        Args:
            data: str. Data to decrypt.
        Returns:
            the resulting plaintext as a string.
        Raises:
            Exception if provided data was not encrypted with this library, or the data was encrypted by a different type of cipher.
        """
        prefix, id, encrypted_data, _ = data.split(":", maxsplit=4)
        if prefix != "enc":
            raise Exception("Attempted to decrypt non-encrypted data")
        if id != self.cipherId:
            raise Exception("Attempted to use wrong cipher to decrypt data")
        return self.cipher.decrypt(encrypted_data)


class AesGcmCipher(Cipher):
    """
    AES GCM based cipher.
    """

    # TODO: switch to Google Tink when python support is available

    def __init__(self, key_file: Path):
        self.key = key_file.read_bytes()
        self.json_keys = ["nonce", "ciphertext", "tag"]

    def encrypt(self, data: str) -> str:
        cipher = AES.new(self.key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data)

        json_values = [
            # convert bytes to string
            b64encode(x).decode("utf-8")
            for x in (cipher.nonce, ciphertext, tag)
        ]
        json_result = json.dumps(dict(zip(self.json_keys, json_values)))
        # turn the json into a base64 string
        json_bytes = json_result.encode("utf-8")
        return b64encode(json_bytes).decode("utf-8")

    def decrypt(self, data: str) -> str:
        # convert base64 string into json text
        json_text = b64decode(data).decode("utf-8")
        json_data = json.loads(json_text)
        # convert string values to bytes
        json_values = {k: b64decode(json_data[k]) for k in self.json_keys}

        cipher = AES.new(self.key, AES.MODE_GCM, json_values["nonce"])
        result = cipher.decrypt_and_verify(
            json_values["ciphertext"], json_values["tag"]
        )
        return result.decode("utf-8")

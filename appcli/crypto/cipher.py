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
from base64 import b64decode, b64encode
from enum import Enum, unique
from pathlib import Path

# vendor libraries
from Crypto.Cipher import AES


@unique
class CipherType(Enum):
    """
    Enum of all supported Cipher types. This maps a cipher implementation to an id.
    The values of the enums should never change, or you may cause backwards-compatibility issues.
    """

    AES_GCM = "1"


class Cipher:
    """
    Factory for getting a Cipher.
    """

    def __init__(self, key_file: Path, cipherType: CipherType = CipherType.AES_GCM):
        """
        Args:
            key_file: Path. Key file to use for encryption/decryption.
            cipherType: str. Identifier of the cipher to use.
        """

        self.cipherId = cipherType.value
        # Since there's only one CipherType to deal with, use AesGcmCipher
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
        return f"enc:id={self.cipherId}:{result}:end"

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
        prefix, metadata, encrypted_data, suffix = data.split(":", maxsplit=4)
        if prefix != "enc" or suffix != "end":
            raise Exception(
                f"Encrypted data must have format [enc:<metadata>:<data>:end]. Data found was [{data}]"
            )
        metadata_map = {
            k: v for k, v in (item.split("=") for item in metadata.split(","))
        }
        if metadata_map["id"] != self.cipherId:
            raise Exception(
                f"Attempted to use wrong cipher [{self.cipherId}] to decrypt data [{data}]"
            )
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

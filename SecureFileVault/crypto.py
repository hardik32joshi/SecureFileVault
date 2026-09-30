"""
crypto.py
----------
Core encryption/decryption logic using Fernet (AES-128-CBC + HMAC under
the hood — note: Fernet's underlying cipher is AES-128, but combined with
HMAC-SHA256 authentication it provides "authenticated encryption", which
is what actually matters for security. We derive the KEY using PBKDF2-
HMAC-SHA256 with a 256-bit output, which is what satisfies the
"AES-256 key derivation" requirement of this project.)

RESPONSIBILITY OF THIS MODULE:
Given a ready-made encryption KEY (produced by auth.py), this module's
ONLY job is to encrypt and decrypt raw bytes/files. It does NOT know
about passwords, salts, or GUI — full separation of concerns.

FILE FORMAT WE DESIGN:
When we encrypt a file, we don't just save the ciphertext — we also need
to store the SALT (so we can re-derive the same key later when decrypting
with the correct password). Our encrypted file format is:

    [16 bytes: salt] + [Fernet token: encrypted data]

This is a simple, explicit, and explainable format — good for a viva.
"""

import os
from cryptography.fernet import Fernet, InvalidToken

from auth import AuthManager


# How many bytes we reserve at the start of every encrypted file for the salt.
SALT_SIZE = 16


class CryptoEngine:
    """
    Handles the actual encryption and decryption of file contents.
    """

    def __init__(self):
        # We reuse AuthManager's key derivation logic rather than
        # duplicating it here — keeps password logic in ONE place.
        self.auth_manager = AuthManager()

    def encrypt_file(self, input_path: str, output_path: str, password: str):
        """
        Encrypt a file of ANY type and write the result to output_path.

        Steps:
          1. Generate a fresh random salt for this file.
          2. Derive a key from the password + salt (PBKDF2).
          3. Read the original file's raw bytes.
          4. Encrypt those bytes with Fernet (AES + HMAC).
          5. Write [salt + encrypted_data] to the output file.

        Args:
            input_path (str): path to the original (plaintext) file.
            output_path (str): where to save the encrypted file.
            password (str): the password chosen by the user.

        Raises:
            FileNotFoundError: if input_path doesn't exist.
            Exception: re-raised for the caller (GUI/app) to handle & log.
        """
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Step 1: fresh salt, unique to this encryption operation.
        salt = self.auth_manager.generate_salt()

        # Step 2: derive the AES key from the password + salt.
        key = self.auth_manager.derive_key(password, salt)

        # Step 3: read the entire original file as raw bytes.
        # "rb" = read binary, which works correctly for images, PDFs,
        # videos, zip files, etc. — not just plain text.
        with open(input_path, "rb") as f:
            plaintext_data = f.read()

        # Step 4: encrypt using Fernet. Fernet internally handles:
        #   - Random IV (initialization vector) generation
        #   - AES encryption in CBC mode
        #   - HMAC authentication tag (tamper detection)
        #   - Timestamp embedding (for optional expiry checks)
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(plaintext_data)

        # Step 5: write salt followed by encrypted data to the output file.
        # Storing the salt alongside the ciphertext is safe — a salt is
        # NOT secret, it just needs to be unpredictable and unique.
        with open(output_path, "wb") as f:
            f.write(salt + encrypted_data)

    def decrypt_file(self, input_path: str, output_path: str, password: str):
        """
        Decrypt a file that was produced by encrypt_file().

        Steps:
          1. Read the encrypted file's raw bytes.
          2. Split off the first SALT_SIZE bytes -> the salt.
          3. Re-derive the key using the SAME salt + the given password.
          4. Decrypt the remaining bytes with Fernet.
          5. Write the recovered plaintext to output_path.

        Args:
            input_path (str): path to the encrypted (.enc) file.
            output_path (str): where to save the recovered original file.
            password (str): the password the user believes is correct.

        Raises:
            FileNotFoundError: if input_path doesn't exist.
            ValueError: if the file is too short to contain a valid salt.
            InvalidToken: if the password is wrong OR the file is corrupted/
                          tampered with (Fernet can't tell these apart,
                          which is intentional — it prevents attackers from
                          learning *why* decryption failed).
        """
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Encrypted file not found: {input_path}")

        with open(input_path, "rb") as f:
            file_contents = f.read()

        if len(file_contents) < SALT_SIZE:
            raise ValueError("File is too short to be a valid encrypted file.")

        # Step 2: split the salt back out from the front of the file.
        salt = file_contents[:SALT_SIZE]
        encrypted_data = file_contents[SALT_SIZE:]

        # Step 3: re-derive the exact same key, IF the password is correct.
        # (Same password + same salt + same iterations = same key, always.)
        key = self.auth_manager.derive_key(password, salt)

        fernet = Fernet(key)

        try:
            # Step 4: attempt decryption. This will raise InvalidToken if
            # the key is wrong (wrong password) or data was tampered with.
            decrypted_data = fernet.decrypt(encrypted_data)
        except InvalidToken:
            # Re-raise with a clearer message for the rest of the app to
            # catch and show the user a friendly error.
            raise InvalidToken(
                "Decryption failed: wrong password or corrupted/tampered file."
            )

        # Step 5: write the recovered original bytes to disk.
        with open(output_path, "wb") as f:
            f.write(decrypted_data)

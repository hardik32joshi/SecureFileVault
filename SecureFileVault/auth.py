"""
auth.py
--------
Everything related to PASSWORDS lives here:
  - Deriving a secure encryption key from a password (PBKDF2-HMAC-SHA256)
  - Checking password strength
  - Generating strong random passwords

WHY SEPARATE FROM crypto.py?
crypto.py should only care about "given a KEY, encrypt/decrypt data."
It shouldn't need to know HOW that key was produced. This separation
means we could swap PBKDF2 for a different KDF (like Argon2) later by
only changing auth.py — crypto.py would not need to change at all.
"""

import base64
import secrets
import string

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Number of PBKDF2 iterations. Higher = slower to brute-force, but also
# slower for the legitimate user. 390,000 is in line with current
# (2024+) OWASP recommendations for PBKDF2-HMAC-SHA256.
PBKDF2_ITERATIONS = 390_000

# Fernet requires a 32-byte (256-bit) key.
KEY_LENGTH_BYTES = 32


class AuthManager:
    """
    Handles password-to-key derivation and password quality checks.
    """

    @staticmethod
    def generate_salt() -> bytes:
        """
        Generate a cryptographically secure random salt.

        WHY A SALT?
        Without a salt, two users with the same password would get the
        SAME derived key, and attackers could precompute hash tables
        ("rainbow tables") for common passwords. A random salt makes
        every derived key unique, even for identical passwords.

        Returns:
            bytes: 16 random bytes (128 bits), which is standard practice.
        """
        # secrets.token_bytes uses the OS's cryptographically secure
        # random number generator — NOT Python's `random` module, which
        # is predictable and unsafe for security purposes.
        return secrets.token_bytes(16)

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """
        Turn a human password into a secure 32-byte encryption key using
        PBKDF2-HMAC-SHA256.

        Args:
            password (str): the user's plaintext password.
            salt (bytes): a random salt (unique per file/user).

        Returns:
            bytes: a base64-encoded 32-byte key, ready for use with Fernet.
        """
        # Build the PBKDF2 key derivation function object.
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),   # Underlying hash function.
            length=KEY_LENGTH_BYTES,     # We want a 32-byte output key.
            salt=salt,                   # The random salt generated above.
            iterations=PBKDF2_ITERATIONS # Repeat hashing this many times.
        )

        # Derive the raw key bytes from the password.
        # .encode() converts the password string into bytes (UTF-8),
        # since cryptographic functions operate on bytes, not text.
        raw_key = kdf.derive(password.encode("utf-8"))

        # Fernet expects the key to be base64 URL-safe encoded.
        return base64.urlsafe_b64encode(raw_key)

    @staticmethod
    def check_password_strength(password: str) -> dict:
        """
        Score a password's strength using simple, explainable rules.
        This is NOT a machine-learning model — it's transparent rule-based
        scoring, which is easier to explain in a viva and good enough for
        an educational security tool.

        Args:
            password (str): the password to evaluate.

        Returns:
            dict: {
                "score": int (0-5),
                "label": str ("Very Weak" ... "Very Strong"),
                "suggestions": list[str]
            }
        """
        score = 0
        suggestions = []

        # --- Rule 1: Length ---
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            suggestions.append("Use at least 8 characters (12+ is better).")

        # --- Rule 2: Character variety ---
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in string.punctuation for c in password)

        variety_count = sum([has_upper, has_lower, has_digit, has_symbol])
        score += variety_count  # +1 point per character category present.

        if not has_upper:
            suggestions.append("Add at least one uppercase letter.")
        if not has_lower:
            suggestions.append("Add at least one lowercase letter.")
        if not has_digit:
            suggestions.append("Add at least one number.")
        if not has_symbol:
            suggestions.append("Add at least one special character (e.g. !@#$).")

        # --- Rule 3: Common weak passwords ---
        common_weak = {"password", "123456", "qwerty", "letmein", "admin", "111111"}
        if password.lower() in common_weak:
            score = 0
            suggestions = ["This is a extremely common password. Choose something unique."]

        # Cap score at 5 for a clean 0-5 scale.
        score = min(score, 5)

        # Map numeric score to a human-readable label.
        labels = {
            0: "Very Weak",
            1: "Weak",
            2: "Fair",
            3: "Good",
            4: "Strong",
            5: "Very Strong",
        }

        return {
            "score": score,
            "label": labels[score],
            "suggestions": suggestions,
        }

    @staticmethod
    def generate_strong_password(length: int = 16) -> str:
        """
        Generate a cryptographically secure random password containing
        uppercase, lowercase, digits, and symbols.

        WHY `secrets` AND NOT `random`?
        Python's `random` module is a Pseudo-Random Number Generator (PRNG)
        designed for simulations/games — its output CAN be predicted if an
        attacker learns its internal state. `secrets` is built on the OS's
        cryptographically secure random source, making it safe for
        generating passwords, tokens, and keys.

        Args:
            length (int): desired password length (default 16).

        Returns:
            str: a randomly generated strong password.
        """
        if length < 8:
            length = 8  # Enforce a sane minimum.

        # Character pool: all letters, digits, and common symbols.
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"

        while True:
            # Randomly pick `length` characters from the pool.
            password = "".join(secrets.choice(alphabet) for _ in range(length))

            # Make sure the generated password actually satisfies variety
            # rules (there's a tiny chance random picks miss a category).
            if (any(c.isupper() for c in password)
                    and any(c.islower() for c in password)
                    and any(c.isdigit() for c in password)
                    and any(c in "!@#$%^&*()-_=+" for c in password)):
                return password

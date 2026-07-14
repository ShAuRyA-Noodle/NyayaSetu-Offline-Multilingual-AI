"""
AES-256-GCM authenticated encryption for data at rest.

Design:
- **AES-256-GCM**: confidentiality + integrity (tamper detection) in one pass.
  A modified ciphertext fails to decrypt rather than returning garbage.
- **Key derivation**: a 256-bit key is derived from a master secret via
  **scrypt** with a per-deployment random salt (stored beside the data). The
  master secret comes from ``NYAYASETU_ENC_KEY`` (preferred) or falls back to
  ``JWT_SECRET_KEY``. A raw 32-byte base64 key can also be supplied directly.
- **Token format**: ``v1`` || nonce(12) || ciphertext+tag, base64url-encoded.
  The version prefix allows future algorithm rotation.

Every ciphertext is self-describing and portable across processes as long as
the same master secret + salt are available.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

VERSION = b"v1"
NONCE_BYTES = 12
KEY_BYTES = 32  # AES-256
SALT_BYTES = 16
_SCRYPT_N = 2 ** 15
_SCRYPT_R = 8
_SCRYPT_P = 1

# Default location for the KDF salt (co-located with the local data store).
DEFAULT_SALT_PATH = os.getenv("NYAYASETU_ENC_SALT_PATH", "data/.enc_salt")


class CryptoError(RuntimeError):
    """Raised on decryption failure (wrong key, tampering, or corruption)."""


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _load_or_create_salt(salt_path: str) -> bytes:
    """Load the KDF salt, creating a random one on first use."""
    p = Path(salt_path)
    if p.exists():
        return p.read_bytes()
    p.parent.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(SALT_BYTES)
    # 0o600 where supported; harmless on Windows.
    p.write_bytes(salt)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return salt


def derive_key(master_secret: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from a master secret using scrypt."""
    kdf = Scrypt(salt=salt, length=KEY_BYTES, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(master_secret.encode("utf-8"))


class AES256GCM:
    """AES-256-GCM cipher for encrypting/decrypting bytes and strings."""

    def __init__(self, key: bytes):
        if len(key) != KEY_BYTES:
            raise ValueError(f"Key must be {KEY_BYTES} bytes (got {len(key)})")
        self._aes = AESGCM(key)

    # ---- factory constructors ---------------------------------------------

    @classmethod
    def from_secret(
        cls,
        master_secret: Optional[str] = None,
        salt_path: str = DEFAULT_SALT_PATH,
    ) -> "AES256GCM":
        """Build a cipher from a master secret (env-derived if not given)."""
        secret = (
            master_secret
            or os.getenv("NYAYASETU_ENC_KEY")
            or os.getenv("JWT_SECRET_KEY")
        )
        if not secret:
            raise CryptoError(
                "No encryption secret. Set NYAYASETU_ENC_KEY (or JWT_SECRET_KEY)."
            )
        salt = _load_or_create_salt(salt_path)
        return cls(derive_key(secret, salt))

    @classmethod
    def from_raw_key(cls, key_b64: str) -> "AES256GCM":
        """Build a cipher from a raw base64-encoded 32-byte key."""
        return cls(_b64d(key_b64))

    # ---- core ops ----------------------------------------------------------

    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> str:
        """Encrypt bytes → base64url token (version || nonce || ct+tag)."""
        nonce = os.urandom(NONCE_BYTES)
        ct = self._aes.encrypt(nonce, plaintext, aad)
        return _b64e(VERSION + nonce + ct)

    def decrypt(self, token: str, aad: Optional[bytes] = None) -> bytes:
        """Decrypt a token produced by :meth:`encrypt`. Raises on tampering."""
        try:
            raw = _b64d(token)
        except Exception as e:  # noqa: BLE001
            raise CryptoError("Malformed ciphertext token") from e
        if raw[: len(VERSION)] != VERSION:
            raise CryptoError("Unsupported ciphertext version")
        body = raw[len(VERSION):]
        nonce, ct = body[:NONCE_BYTES], body[NONCE_BYTES:]
        try:
            return self._aes.decrypt(nonce, ct, aad)
        except Exception as e:  # InvalidTag etc.
            raise CryptoError("Decryption failed (wrong key or tampered data)") from e

    def encrypt_str(self, text: str, aad: Optional[bytes] = None) -> str:
        return self.encrypt(text.encode("utf-8"), aad)

    def decrypt_str(self, token: str, aad: Optional[bytes] = None) -> str:
        return self.decrypt(token, aad).decode("utf-8")


# ---- module-level convenience (lazy singleton) ----------------------------

_default_cipher: Optional[AES256GCM] = None


def get_default_cipher() -> AES256GCM:
    """Return a process-wide cipher derived from the env master secret."""
    global _default_cipher
    if _default_cipher is None:
        _default_cipher = AES256GCM.from_secret()
    return _default_cipher


def encrypt_str(text: str, aad: Optional[bytes] = None) -> str:
    """Encrypt a string with the default env-derived cipher."""
    return get_default_cipher().encrypt_str(text, aad)


def decrypt_str(token: str, aad: Optional[bytes] = None) -> str:
    """Decrypt a string with the default env-derived cipher."""
    return get_default_cipher().decrypt_str(token, aad)

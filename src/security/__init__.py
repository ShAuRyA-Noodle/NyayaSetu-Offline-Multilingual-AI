"""
Security package — at-rest data protection for the offline-first deployment.

Rural/kiosk devices hold citizen PII (grievance text, contact details) and the
local knowledge base on disk, often on shared or physically-accessible
hardware. This package provides:

- ``crypto``    : AES-256-GCM authenticated encryption for data at rest.
- ``integrity`` : SHA-256 manifests to detect tampering/corruption of the
                  local knowledge base and index files.

Complements the existing in-transit protections (JWT, bcrypt, TLS).
"""

from .crypto import (
    AES256GCM,
    CryptoError,
    decrypt_str,
    encrypt_str,
    get_default_cipher,
)
from .integrity import (
    IntegrityError,
    compute_sha256,
    verify_manifest,
    write_manifest,
)

__all__ = [
    "AES256GCM",
    "CryptoError",
    "encrypt_str",
    "decrypt_str",
    "get_default_cipher",
    "IntegrityError",
    "compute_sha256",
    "write_manifest",
    "verify_manifest",
]

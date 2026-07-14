"""
Tests for at-rest encryption (AES-256-GCM) and SHA-256 integrity manifests.
"""

import os

import pytest

from src.security.crypto import AES256GCM, CryptoError, derive_key
from src.security.integrity import (
    IntegrityError,
    compute_sha256,
    verify_manifest,
    verify_or_raise,
    write_manifest,
)


# ---- crypto ----------------------------------------------------------------


def _cipher(tmp_path, secret="master-secret-123"):
    salt_path = tmp_path / ".enc_salt"
    return AES256GCM.from_secret(secret, salt_path=str(salt_path))


def test_encrypt_decrypt_roundtrip(tmp_path):
    c = _cipher(tmp_path)
    plaintext = "किसान की शिकायत: भुगतान में देरी हुई है"  # real Hindi grievance text
    token = c.encrypt_str(plaintext)
    assert token != plaintext
    assert c.decrypt_str(token) == plaintext


def test_key_is_256_bits(tmp_path):
    key = derive_key("secret", b"0123456789abcdef")
    assert len(key) == 32  # AES-256


def test_wrong_key_fails(tmp_path):
    c1 = _cipher(tmp_path / "a", secret="secret-one")
    token = c1.encrypt_str("sensitive")
    c2 = _cipher(tmp_path / "b", secret="secret-two")
    with pytest.raises(CryptoError):
        c2.decrypt_str(token)


def test_tampered_ciphertext_rejected(tmp_path):
    c = _cipher(tmp_path)
    token = c.encrypt_str("do not tamper")
    # Flip a character in the middle of the base64 token.
    bad = list(token)
    mid = len(bad) // 2
    bad[mid] = "A" if bad[mid] != "A" else "B"
    with pytest.raises(CryptoError):
        c.decrypt_str("".join(bad))


def test_aad_binding(tmp_path):
    c = _cipher(tmp_path)
    token = c.encrypt_str("payload", aad=b"grievance:42")
    # Decrypting with different associated data must fail (GCM auth).
    with pytest.raises(CryptoError):
        c.decrypt_str(token, aad=b"grievance:99")
    assert c.decrypt_str(token, aad=b"grievance:42") == "payload"


def test_missing_secret_raises(monkeypatch):
    monkeypatch.delenv("NYAYASETU_ENC_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(CryptoError):
        AES256GCM.from_secret()


# ---- integrity -------------------------------------------------------------


def test_manifest_verifies_clean(tmp_path):
    f1 = tmp_path / "index.bin"
    f2 = tmp_path / "meta.json"
    f1.write_bytes(b"\x00\x01\x02fake-faiss-index")
    f2.write_text('{"schemes": 4347}', encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest([f1, f2], manifest, base_dir=tmp_path)
    ok, problems = verify_manifest(manifest)
    assert ok and problems == []


def test_manifest_detects_corruption(tmp_path):
    f1 = tmp_path / "index.bin"
    f1.write_bytes(b"original-content")
    manifest = tmp_path / "manifest.json"
    write_manifest([f1], manifest, base_dir=tmp_path)
    # Corrupt the file after manifest creation.
    f1.write_bytes(b"corrupted-content")
    ok, problems = verify_manifest(manifest)
    assert not ok
    assert any("hash mismatch" in p for p in problems)
    with pytest.raises(IntegrityError):
        verify_or_raise(manifest)


def test_manifest_detects_missing_file(tmp_path):
    f1 = tmp_path / "index.bin"
    f1.write_bytes(b"data")
    manifest = tmp_path / "manifest.json"
    write_manifest([f1], manifest, base_dir=tmp_path)
    f1.unlink()
    ok, problems = verify_manifest(manifest)
    assert not ok and any("missing file" in p for p in problems)


def test_sha256_matches_hashlib(tmp_path):
    import hashlib
    f = tmp_path / "x.bin"
    data = os.urandom(4096)
    f.write_bytes(data)
    assert compute_sha256(f) == hashlib.sha256(data).hexdigest()

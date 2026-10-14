"""Symmetric encryption helpers for stored integration configurations.

Key derivation (deterministic, no extra secret to manage):
    Fernet key = urlsafe_base64(sha256(settings.secret_key))

Consequence (by design): rotating SECRET_KEY invalidates every previously stored
configuration blob - integrations must be re-entered after a key rotation.

The encrypted payload is always the UTF-8 JSON of a dict; plaintext never leaves
this module, and callers must never echo decrypted secrets back to clients.
"""
from __future__ import annotations

import base64
import hashlib
import json

from app.core.config import get_settings


def fernet():
    """A Fernet instance keyed from the application SECRET_KEY."""
    from cryptography.fernet import Fernet  # imported lazily: only needed when a blob is touched

    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_dict(config: dict) -> str:
    """Encrypt a dict (JSON) -> ASCII token string safe to store in a TEXT column."""
    return fernet().encrypt(json.dumps(config).encode("utf-8")).decode("ascii")


def decrypt_dict(token: str) -> dict:
    """Reverse of encrypt_dict. Raises on a wrong key / tampered ciphertext."""
    return json.loads(fernet().decrypt(token.encode("ascii")))


def encrypt(plaintext: str) -> str:
    return fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return fernet().decrypt(token.encode("ascii")).decode("utf-8")


__all__ = ["fernet", "encrypt_dict", "decrypt_dict", "encrypt", "decrypt"]

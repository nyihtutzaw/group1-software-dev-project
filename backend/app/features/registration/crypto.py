"""F1 evidence encryption — the mechanism behind erasure (#45, ADR 0010).

Every evidence file is encrypted with its own AES-256-GCM key before it is sealed. The
ciphertext goes to the write-once backend; the key goes to `evidence_keys`, which is an
ordinary table with no write-once trigger.

That split is the whole idea. Destroying the key makes one file's content unrecoverable
without updating or deleting anything that is supposed to be permanent: the ciphertext stays
in the bucket under its retention lock, the `evidence_files` row stays exactly as sealed, and
the ledger's hash chain still verifies.

GCM also authenticates: a ciphertext altered in the bucket fails to decrypt rather than
returning wrong bytes.
"""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32  # AES-256
NONCE_BYTES = 12  # GCM standard


class EvidenceUndecryptableError(Exception):
    """The ciphertext does not match the key — it was altered, or the key is the wrong one."""


def new_key() -> bytes:
    """A fresh key for one file. Never reused: erasing one file must not affect another."""
    return AESGCM.generate_key(bit_length=KEY_BYTES * 8)


def encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Return (nonce, ciphertext). The nonce is public; it is stored beside the key."""
    nonce = os.urandom(NONCE_BYTES)
    return nonce, AESGCM(key).encrypt(nonce, plaintext, None)


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """Return the plaintext, or raise if the ciphertext was tampered with."""
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag as error:
        raise EvidenceUndecryptableError from error

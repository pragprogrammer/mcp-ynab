"""AES-256-GCM for the local cache of budget data.

The cache holds payees, memos, amounts and category names — a fairly complete
picture of the user's finances — in a SQLite file under the user profile. This
encrypts the payload columns so that file is not readable on its own.

The key lives in the OS credential store next to the token, which means the
protection is exactly as strong as that store: it defends against something
reading the DB file (a backup, a synced folder, another account on the machine),
not against code running as the same user. SECURITY.md spells that out.

SQLCipher would encrypt the whole file but needs a native build, which is
painful on Windows; this is a column-level scheme instead, so the columns used
for lookups and delta sync stay in plaintext and still leak metadata.
"""

import base64
import os

from src.security import credentials

KEY_BYTES = 32  # AES-256
NONCE_BYTES = 12  # GCM standard nonce size


class CacheEncryptionUnavailable(RuntimeError):
    """Raised when cache encryption is on but no key can be stored or read."""


class CacheDecryptionError(RuntimeError):
    """Raised when a cached row cannot be decrypted with the current key."""


_enabled = True
_key: bytes | None = None


def configure(*, enabled: bool) -> None:
    """Turn cache encryption on or off for this process."""
    global _enabled, _key
    _enabled = enabled
    if not enabled:
        _key = None


def is_enabled() -> bool:
    return _enabled


def reset_key_cache() -> None:
    """Forget the in-memory key. For tests."""
    global _key
    _key = None


def aad_for(table: str, column: str) -> bytes:
    """Additional authenticated data binding a ciphertext to its table and column.

    Deliberately not row-scoped: see SECURITY.md for the row-swap limitation this
    leaves open, which is acceptable because it requires DB write access already.
    """
    return f"mcp-ynab:{table}.{column}".encode("utf-8")


def load_or_create_key() -> bytes:
    """Fetch the cache key from the credential store, creating it on first use."""
    global _key
    if _key is not None:
        return _key

    stored = credentials.get_secret(credentials.CACHE_KEY_ENTRY)
    if stored:
        try:
            key = base64.b64decode(stored, validate=True)
        except Exception as e:
            raise CacheEncryptionUnavailable(
                "The stored cache key is not valid base64. Run `mcp-ynab cache purge` "
                "to discard the cache and its key."
            ) from e
        if len(key) != KEY_BYTES:
            raise CacheEncryptionUnavailable(
                f"The stored cache key is {len(key)} bytes, expected {KEY_BYTES}. "
                "Run `mcp-ynab cache purge`."
            )
        _key = key
        return key

    key = os.urandom(KEY_BYTES)
    try:
        credentials.set_secret(credentials.CACHE_KEY_ENTRY, base64.b64encode(key).decode("ascii"))
    except credentials.CredentialStoreUnavailable as e:
        # Fail closed. Quietly writing plaintext instead would leave the user
        # believing their cache is encrypted when it is not.
        raise CacheEncryptionUnavailable(
            f"{e}\nCache encryption needs somewhere to keep its key. Set "
            "YNAB_CACHE_ENCRYPTION=0 to store the cache in plaintext instead — an "
            "explicit choice, not a silent downgrade."
        ) from e
    _key = key
    return key


def encrypt(plaintext: bytes, aad: bytes, *, key: bytes | None = None) -> bytes:
    """Encrypt to `nonce(12) || ciphertext || tag`."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = key if key is not None else load_or_create_key()
    nonce = os.urandom(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt(envelope: bytes, aad: bytes, *, key: bytes | None = None) -> bytes:
    """Reverse encrypt(). Raises InvalidTag on tampering, wrong AAD, or wrong key."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = key if key is not None else load_or_create_key()
    if len(envelope) <= NONCE_BYTES:
        raise ValueError("ciphertext envelope is too short to contain a nonce")
    nonce, body = envelope[:NONCE_BYTES], envelope[NONCE_BYTES:]
    return AESGCM(key).decrypt(nonce, body, aad)

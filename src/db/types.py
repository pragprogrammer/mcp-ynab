"""SQLAlchemy column type that encrypts JSON payloads at rest.

Implemented as a TypeDecorator so encryption is transparent to
`src/cache/service.py`: it keeps handing dicts and lists to the ORM and getting
them back, and nothing at the call sites had to change.
"""

import json

from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from src.security import crypto

# One framing byte in front of the stored blob, so a database written with
# encryption off can still be read after it is turned on (and vice versa) rather
# than decoding as garbage. crypto.encrypt()'s own envelope stays exactly
# nonce || ciphertext || tag; this byte belongs to the storage layer.
_PLAINTEXT = b"\x00"
_AESGCM = b"\x01"


class EncryptedJSON(TypeDecorator):
    """JSON in Python, an encrypted BLOB in SQLite."""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, table: str, column: str, **kwargs):
        super().__init__(**kwargs)
        # Named to match the constructor parameters so SQLAlchemy's cache key
        # introspection distinguishes two instances bound to different columns.
        self.table = table
        self.column = column

    @property
    def _aad(self) -> bytes:
        return crypto.aad_for(self.table, self.column)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        if not crypto.is_enabled():
            return _PLAINTEXT + raw
        return _AESGCM + crypto.encrypt(raw, self._aad)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        version, body = value[:1], value[1:]
        if version == _PLAINTEXT:
            return json.loads(body)
        if version != _AESGCM:
            raise crypto.CacheDecryptionError(
                f"Unrecognised cache envelope version {version!r}. "
                "Run `mcp-ynab cache purge`."
            )
        try:
            return json.loads(crypto.decrypt(body, self._aad))
        except crypto.CacheEncryptionUnavailable:
            raise
        except Exception as e:
            # Usually the key was removed while the DB survived. The cache is
            # disposable, so say so instead of failing cryptically.
            raise crypto.CacheDecryptionError(
                "A cached row could not be decrypted with the current cache key. "
                "Run `mcp-ynab cache purge` to discard the cache and start over."
            ) from e

"""OS credential store access for the YNAB token and the cache encryption key.

Secrets are held in the platform credential store via `keyring` — Windows
Credential Manager, macOS Keychain, or Secret Service on Linux — instead of in a
config file. The point is to keep the token out of every file an agent can read
(`~/.claude.json`, `claude_desktop_config.json`, `.env.local`, shell history).

It is *not* a sandbox: these stores scope secrets to the logged-in user, not to a
particular program, so anything running as the same user can ask for the same
secret. SECURITY.md states that limit plainly; do not imply otherwise here.
"""

import hashlib
import sys

SERVICE_NAME = "mcp-ynab"
API_KEY_ENTRY = "api_key"
CACHE_KEY_ENTRY = "cache_key"

_NO_BACKEND_HINT = (
    "No OS credential store is available to `keyring` on this machine.\n"
    "  - Linux: install a Secret Service provider (gnome-keyring, KWallet) or\n"
    "    `pip install keyrings.alt` for a file-backed store.\n"
    "  - Headless/CI: set YNAB_API_KEY in the environment instead.\n"
    "See SECURITY.md for the trade-offs."
)


class CredentialStoreUnavailable(RuntimeError):
    """Raised when no usable `keyring` backend is installed."""


def _keyring():
    """Import keyring lazily.

    Importing it can be slow (it probes backends) and the server should not pay
    that cost on a run that never touches the credential store.
    """
    import keyring

    return keyring


def _no_keyring_error() -> type[BaseException]:
    from keyring.errors import NoKeyringError

    return NoKeyringError


def get_secret(entry: str) -> str | None:
    """Read one secret, or None if it is absent.

    A missing backend is reported as absence rather than an exception so the
    server can fall through to the next credential source.
    """
    try:
        return _keyring().get_password(SERVICE_NAME, entry)
    except _no_keyring_error():
        return None
    except Exception as e:  # backend present but unhappy (locked keyring, etc.)
        print(f"WARNING: credential store read failed: {e}", file=sys.stderr)
        return None


def set_secret(entry: str, value: str) -> None:
    """Write one secret. Raises CredentialStoreUnavailable if there is no backend."""
    try:
        _keyring().set_password(SERVICE_NAME, entry, value)
    except _no_keyring_error() as e:
        raise CredentialStoreUnavailable(_NO_BACKEND_HINT) from e


def delete_secret(entry: str) -> bool:
    """Delete one secret. Returns False if it was not there to begin with."""
    keyring = _keyring()
    try:
        if keyring.get_password(SERVICE_NAME, entry) is None:
            return False
        keyring.delete_password(SERVICE_NAME, entry)
        return True
    except _no_keyring_error() as e:
        raise CredentialStoreUnavailable(_NO_BACKEND_HINT) from e
    except Exception:
        return False


# ── YNAB personal access token ───────────────────────────────


def store_token(token: str) -> None:
    set_secret(API_KEY_ENTRY, token)


def load_token() -> str | None:
    return get_secret(API_KEY_ENTRY)


def delete_token() -> bool:
    return delete_secret(API_KEY_ENTRY)


def token_fingerprint(token: str | None) -> str:
    """A safe-to-log identifier for a token.

    Never returns the token. Short values get the digest alone, because first-4 +
    last-4 of a short string is most of the string.
    """
    if not token:
        return "(none)"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    if len(token) < 16:
        return f"sha256:{digest}"
    return f"{token[:4]}...{token[-4:]} (sha256:{digest})"

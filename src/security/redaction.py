"""Keep live secrets out of anything the model can read.

The YNAB token travels in an Authorization header. httpx exception reprs and
YNAB error bodies can echo request headers back, so every string that leaves a
tool by an error path is filtered here first.

This is a backstop, not the primary defence: the token is a SecretStr everywhere
except the one line that builds the header. Backstops are cheap, and the failure
mode they cover (a token in a tool result the model reads) is the one that
matters.
"""

PLACEHOLDER = "***REDACTED***"

# Below this length a "secret" is more likely to be a substring of ordinary text
# than the real thing, and replacing it would corrupt messages without adding
# protection. A YNAB personal access token is 64 characters.
_MIN_SECRET_LEN = 8

_secrets: set[str] = set()


def register_secret(value: str | None) -> None:
    """Register a live secret to be scrubbed from outbound text."""
    if value and len(value) >= _MIN_SECRET_LEN:
        _secrets.add(value)


def forget_secrets() -> None:
    """Drop every registered secret. For tests."""
    _secrets.clear()


def scrub(text: str) -> str:
    """Replace every registered secret in `text` with a placeholder."""
    if not text or not _secrets:
        return text
    # Longest first, so a secret that contains another is replaced whole.
    for secret in sorted(_secrets, key=len, reverse=True):
        if secret in text:
            text = text.replace(secret, PLACEHOLDER)
    return text

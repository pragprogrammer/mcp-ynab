"""Security primitives: credential storage, redaction, cache encryption, consent.

Nothing in this package imports the server or the cache service, so it can be
used from `src/cli.py` without pulling in a `Settings` that demands a token.
"""

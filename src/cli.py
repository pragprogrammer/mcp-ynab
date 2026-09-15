"""Command line entry point for `mcp-ynab`.

A bare invocation starts the MCP stdio server, so existing client configs keep
working untouched. Subcommands manage the credential store and the local cache.

Writing to stdout is fine *here*: these subcommands are run by a human in a
terminal, not over the MCP transport. The server path below prints nothing to
stdout for exactly that reason.

The server modules are imported lazily inside serve(), because importing them
constructs Settings, which refuses to build without a token — `auth login` has
to be runnable before a token exists.
"""

import argparse
import asyncio
import getpass
import os
import re
import sys
from pathlib import Path

from src.security import credentials

# A YNAB personal access token is 64 printable ASCII characters with no spaces.
# The floor below is deliberately loose: the point is to catch input that cannot
# be a token at all, not to encode YNAB's exact format and break when it changes.
_TOKEN_MIN_LEN = 20
_HAS_WHITESPACE = re.compile(r"\s")


def _read_stdin_token() -> str:
    """Read a token from stdin, tolerating a byte-order mark.

    Windows PowerShell 5.1 prefixes anything it pipes to a native executable
    with a UTF-8 BOM. A BOM is not whitespace, so .strip() leaves it in place
    and it then reads as a control character — decoding as utf-8-sig consumes
    it. Any stray BOM elsewhere in the input is dropped too, which clipboard
    and editor round-trips occasionally introduce.
    """
    raw = getattr(sys.stdin, "buffer", None)
    if raw is None:  # stdin already wrapped, e.g. under a test harness
        return sys.stdin.read().replace("﻿", "").strip()
    try:
        text = raw.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return ""
    return text.replace("﻿", "").strip()


def _why_not_a_token(token: str) -> str | None:
    """Explain why `token` cannot be a YNAB token, or None if it might be.

    Worth checking before the network call. A token containing a control
    character builds a malformed Authorization header, and YNAB answers that
    with a bodyless HTTP 400 that says nothing about the actual cause.
    """
    if any(not c.isprintable() for c in token):
        return (
            "the input contains control characters rather than a token.\n"
            "  On the Windows console, Ctrl+V at a hidden prompt is delivered as a\n"
            "  literal control character instead of pasting. Try right-clicking to\n"
            "  paste, or skip pasting entirely with:  auth login --stdin"
        )
    if _HAS_WHITESPACE.search(token):
        return "the input contains whitespace; a YNAB token has none."
    if len(token) < _TOKEN_MIN_LEN:
        return (
            f"the input is {len(token)} character(s); a YNAB personal access token "
            "is 64. A partial paste looks like this."
        )
    return None


def _db_path() -> str:
    """The cache DB path, matching what Settings would resolve."""
    from src.config import _default_db_path

    return os.environ.get("CACHE_DB_PATH") or _default_db_path()


async def _validate_token(token: str) -> tuple[bool, str]:
    """Check a token against the live API. Returns (ok, detail)."""
    import httpx

    from src.ynab_client import YNABClient, YNABError

    client = YNABClient(token)
    try:
        user = await client.get_user()
        return True, f"user id {user.id}"
    except YNABError as e:
        return False, f"YNAB rejected the token: {e.message}"
    except httpx.HTTPStatusError as e:
        # YNAB answered. Do not report that as a failure to reach it.
        return False, f"YNAB rejected the request with HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        return False, f"could not reach YNAB: {type(e).__name__}: {e}"
    except Exception as e:
        return False, f"unexpected failure validating the token: {type(e).__name__}: {e}"
    finally:
        await client.close()


def auth_login(from_stdin: bool = False) -> int:
    """Read a token, validate it, then store it."""
    if from_stdin:
        # For terminals where pasting into a hidden prompt does not work, and
        # for headless setups. Piping from a file keeps the token out of argv
        # and out of shell history, which is the property that matters.
        token = _read_stdin_token()
    else:
        # Both streams, not just stdin. Under Git Bash/MSYS on Windows
        # sys.stdin.isatty() reports True even when stdin is redirected, and
        # getpass resolves to win_getpass, which reads the console directly and
        # ignores the redirect — so a stdin-only check passes and the process
        # then blocks forever waiting for a human who is not there. Requiring
        # stdout to be a terminal too turns that hang into this message.
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print(
                "ERROR: `auth login` needs an interactive terminal. The token is "
                "read with getpass so it never lands in argv or shell history.\n"
                "       To feed it from a file instead: auth login --stdin",
                file=sys.stderr,
            )
            return 2

        print("Paste your YNAB personal access token.")
        print("Create one at https://app.ynab.com/settings/developer\n")
        print("Input is HIDDEN: nothing appears as you type or paste. That is normal.")
        print("If Ctrl+V does nothing, try right-click, or rerun with --stdin.\n")
        token = getpass.getpass("Token: ").strip()

    if not token:
        print("ERROR: no token entered.", file=sys.stderr)
        return 2

    problem = _why_not_a_token(token)
    if problem:
        # Caught here so the user gets the real cause, rather than an opaque
        # rejection from an API that never saw a well-formed request.
        print(f"ERROR: {problem}\nNothing was stored.", file=sys.stderr)
        return 2

    print("Validating against the YNAB API...")
    ok, detail = asyncio.run(_validate_token(token))
    if not ok:
        # Never store something that does not work; a bad token saved now becomes
        # a confusing auth failure later, far from its cause.
        print(f"ERROR: {detail}. Nothing was stored.", file=sys.stderr)
        return 1

    try:
        credentials.store_token(token)
    except credentials.CredentialStoreUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"OK: token validated ({detail}) and stored in the OS credential store.")
    print(f"     fingerprint: {credentials.token_fingerprint(token)}")
    print(
        "\nYou can now remove YNAB_API_KEY from your MCP client config "
        "(~/.claude.json, claude_desktop_config.json) and from .env.local."
    )
    return 0


def auth_status() -> int:
    """Report which credential source is live, without revealing the token."""
    stored = credentials.load_token()
    env = os.environ.get("YNAB_API_KEY")
    allow_env = os.environ.get("YNAB_ALLOW_ENV_KEY", "1").lower() not in ("0", "false", "no")

    if stored:
        source, token = "OS credential store", stored
    elif env and allow_env:
        source, token = "YNAB_API_KEY environment variable (deprecated)", env
    else:
        print("No token available.")
        if env and not allow_env:
            print("  YNAB_API_KEY is set but YNAB_ALLOW_ENV_KEY=0 refuses it.")
        print("  Run `mcp-ynab auth login` to store one.")
        return 1

    print(f"Token source: {source}")
    print(f"Fingerprint:  {credentials.token_fingerprint(token)}")
    if stored and env:
        print(
            "Note:         YNAB_API_KEY is also set in the environment and is being "
            "ignored.\n              Remove it so the token stops sitting in a "
            "readable config file."
        )
    print(f"Cache key:    {'present' if credentials.get_secret(credentials.CACHE_KEY_ENTRY) else 'not yet created'}")
    print(f"Cache DB:     {_db_path()}")
    return 0


def auth_logout() -> int:
    """Delete the stored token."""
    try:
        removed = credentials.delete_token()
    except credentials.CredentialStoreUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("Token deleted." if removed else "No stored token to delete.")
    if os.environ.get("YNAB_API_KEY"):
        print(
            "WARNING: YNAB_API_KEY is still set in the environment, so the server "
            "will keep working from it. Remove it too."
        )
    return 0


def cache_purge() -> int:
    """Delete the cache database and the key that encrypts it."""
    db = Path(_db_path())
    removed = []
    # -wal and -shm are SQLite's WAL sidecars; leaving them behind would leave
    # committed pages of plaintext-adjacent data on disk after a "purge".
    for path in (db, db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")):
        if path.exists():
            path.unlink()
            removed.append(path.name)

    key_removed = False
    try:
        key_removed = credentials.delete_secret(credentials.CACHE_KEY_ENTRY)
    except credentials.CredentialStoreUnavailable as e:
        print(f"WARNING: could not remove the cache key: {e}", file=sys.stderr)

    print(f"Cache files removed: {', '.join(removed) if removed else 'none'}")
    print(f"Cache key removed:   {'yes' if key_removed else 'no (none stored)'}")
    print("The cache rebuilds itself on the next request.")
    return 0


def serve() -> int:
    """Start the MCP stdio server."""
    from src.server import main as server_main

    server_main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-ynab",
        description="MCP server that connects AI assistants to your YNAB budget. "
        "With no subcommand, starts the stdio server.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="start the MCP stdio server (the default)")

    auth = sub.add_parser("auth", help="manage the stored YNAB token")
    auth_sub = auth.add_subparsers(dest="auth_command")
    login = auth_sub.add_parser("login", help="read a token, validate it, store it")
    login.add_argument(
        "--stdin",
        action="store_true",
        help="read the token from stdin instead of prompting, e.g. "
        "`type token.txt | mcp-ynab auth login --stdin`",
    )
    auth_sub.add_parser("status", help="show which credential source is in use")
    auth_sub.add_parser("logout", help="delete the stored token")

    cache = sub.add_parser("cache", help="manage the local cache")
    cache_sub = cache.add_subparsers(dest="cache_command")
    cache_sub.add_parser("purge", help="delete the cache database and its key")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command in (None, "serve"):
        return serve()

    if args.command == "auth":
        if args.auth_command == "login":
            return auth_login(from_stdin=args.stdin)
        handlers = {"status": auth_status, "logout": auth_logout}
        handler = handlers.get(args.auth_command)
        if handler is None:
            parser.parse_args(["auth", "--help"])
            return 2
        return handler()

    if args.command == "cache":
        if args.cache_command != "purge":
            parser.parse_args(["cache", "--help"])
            return 2
        return cache_purge()

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

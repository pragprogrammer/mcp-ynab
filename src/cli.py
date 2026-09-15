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
import sys
from pathlib import Path

from src.security import credentials


def _db_path() -> str:
    """The cache DB path, matching what Settings would resolve."""
    from src.config import _default_db_path

    return os.environ.get("CACHE_DB_PATH") or _default_db_path()


async def _validate_token(token: str) -> tuple[bool, str]:
    """Check a token against the live API. Returns (ok, detail)."""
    from src.ynab_client import YNABClient, YNABError

    client = YNABClient(token)
    try:
        user = await client.get_user()
        return True, f"user id {user.id}"
    except YNABError as e:
        return False, f"YNAB rejected the token: {e.message}"
    except Exception as e:
        return False, f"could not reach YNAB: {type(e).__name__}: {e}"
    finally:
        await client.close()


def auth_login() -> int:
    """Read a token interactively, validate it, then store it."""
    if not sys.stdin.isatty():
        print(
            "ERROR: `auth login` needs a terminal. The token is read with getpass so "
            "it never lands in argv or shell history.",
            file=sys.stderr,
        )
        return 2

    print("Paste your YNAB personal access token (input is hidden).")
    print("Create one at https://app.ynab.com/settings/developer\n")
    token = getpass.getpass("Token: ").strip()
    if not token:
        print("ERROR: no token entered.", file=sys.stderr)
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
    auth_sub.add_parser("login", help="read a token, validate it, store it")
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
        handlers = {"login": auth_login, "status": auth_status, "logout": auth_logout}
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

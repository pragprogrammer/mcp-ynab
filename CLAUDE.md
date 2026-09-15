# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Landing Page (Astro):**
- `cd website && npm run dev` — Start dev server
- `cd website && npm run build` — Production build

**Python MCP Server:**
- `uv run pytest` — Run all tests
- `uv run pytest tests/test_foo.py::test_name` — Run a single test
- `uv run python -m src.server` — Run MCP server standalone (stdio transport)
- `uv run python -m src.cli auth login|status|logout` — Manage the stored token
- `uv run python -m src.cli cache purge` — Delete the cache DB and its key

**Environment:** The token comes from the OS credential store (`mcp-ynab auth
login`) or, with a deprecation warning, from `YNAB_API_KEY` in `.env.local`.
Other flags: `YNAB_ALLOW_ENV_KEY=0` (credential store only), `YNAB_READ_ONLY=1`
(write tools not registered), `YNAB_CACHE_ENCRYPTION=0` (plaintext cache,
debugging only).

## Architecture

This repo contains two things:
1. **A Python MCP server** (`src/`) that connects AI assistants to the YNAB API
2. **A landing page** (`website/`) built with Astro + Tailwind, deployed to Vercel

### Python MCP server (`src/`)

- **`server/`** — MCPServer (mcp SDK 2.x) server package, run standalone via `python -m src.server`. Tool definitions are split by domain across submodules (`accounts.py`, `transactions.py`, `categories.py`, etc.) and registered through `src/server/__init__.py`. Shared infrastructure (`mcp`, `cache`, `client`, `handle_errors`, `serialize` helpers, `DEFAULT_EXCLUDES`) lives in `src/server/_shared.py`. All tools use the `@handle_errors` decorator for uniform YNAB/HTTP error handling and lazy DB init.
- **`ynab_client.py`** — Async httpx client for YNAB API v1.
- **`cache/`** — 4-tier caching: TTL-based response cache, delta sync (server knowledge tracking), retry with exponential backoff, SQLite persistence.
- **`models/`** — Pydantic models, each module exports a `*_DEFAULT_EXCLUDE` set defining the fields hidden from MCP responses by default. The registry in `src/server/_shared.py` (`DEFAULT_EXCLUDES`) maps model classes to their default exclude sets. Every MCP tool accepts an optional `exclude_fields: list[str]` param that, when provided, fully replaces the default. See `FIELDS.md` for the per-model field reference.
- **`security/`** — `credentials.py` (keyring-backed store for the token and the
  cache key), `redaction.py` (scrubs live secrets from every error path),
  `crypto.py` (AES-256-GCM for the cache), `consent.py` + `diff.py` (human
  confirmation with a real before/after diff). See `SECURITY.md` for the threat
  model and its stated limits.
- **`cli.py`** — the `mcp-ynab` entry point. A bare invocation starts the stdio
  server; `auth`/`cache` subcommands manage credentials and the cache. Server
  modules are imported lazily so `auth login` works before a token exists.
- **`config.py`** — `Settings` via pydantic-settings. `ynab_api_key` is a
  `SecretStr` resolved from the credential store first, then the environment.
  Cache DB path is platform-specific (`~/Library/Application Support/ynab-mcp-server/cache.db` on macOS).

### Key conventions

- **Milliunits:** YNAB stores money as milliunits (1000 = $1.00). The Python server accepts dollars in tool parameters and converts to milliunits internally.
- **Month format:** YNAB months use first-of-month dates (`2026-03-01` for March 2026).
- **Mutating tools require consent:** the 16 write tools take a `ctx: Context | None = None`
  parameter (injected by the SDK, invisible in the tool's input schema) and call
  `consent.confirm()` before writing. The pre-image must come from
  `_shared.client`, never the cache — a stale row would show the user a false
  "before". Register them with `_shared.mutating_tool()`, not `_shared.mcp.tool()`,
  so `YNAB_READ_ONLY=1` can drop them at registration time.
- **Dependency bounds:** runtime deps in `pyproject.toml` carry upper bounds. An unbounded `mcp[cli]>=1.26.0` broke every fresh install when the SDK shipped 2.0.0 (#21). `uv run pytest` uses `uv.lock` and cannot catch this class of break; `python scripts/smoke_test.py` resolves fresh from the declared constraints and can. Run it before releasing, and after touching any dependency.

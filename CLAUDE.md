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

**Environment:** Requires `YNAB_API_KEY` in `.env.local`

## Architecture

This repo contains two things:
1. **A Python MCP server** (`src/`) that connects AI assistants to the YNAB API
2. **A landing page** (`website/`) built with Astro + Tailwind, deployed to Vercel

### Python MCP server (`src/`)

- **`server.py`** — FastMCP tool definitions (30+ tools). All tools use the `@handle_errors` decorator for uniform YNAB/HTTP error handling and lazy DB init.
- **`ynab_client.py`** — Async httpx client for YNAB API v1.
- **`cache/`** — 4-tier caching: TTL-based response cache, delta sync (server knowledge tracking), retry with exponential backoff, SQLite persistence.
- **`models/`** — Pydantic models with `*_DISPLAY_EXCLUDE` / `*_INCLUDE` sets that control which fields are serialized back to the LLM (keeps token usage down).
- **`config.py`** — `Settings` via pydantic-settings. Cache DB path is platform-specific (`~/Library/Application Support/ynab-mcp-server/cache.db` on macOS).

### Key conventions

- **Milliunits:** YNAB stores money as milliunits (1000 = $1.00). The Python server accepts dollars in tool parameters and converts to milliunits internally.
- **Month format:** YNAB months use first-of-month dates (`2026-03-01` for March 2026).

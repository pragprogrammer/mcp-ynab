# YNAB MCP Server

An MCP server that connects AI assistants to your [YNAB](https://www.ynab.com/) budget. Ask your budget questions YNAB can't answer.

**[mcp-ynab.com](https://mcp-ynab.com)** — Full setup guide, troubleshooting, and more.

## Features

- **30+ tools** — budgets, accounts, transactions, categories, payees, months, scheduled transactions, and analytics
- **Delta sync** — only fetches what changed since the last call (uses YNAB's server knowledge)
- **4-tier caching** — TTL cache, delta sync, retry with backoff, SQLite persistence
- **Search & analytics** — text search across transactions, per-category spending breakdowns, Sankey flow data
- **Bulk operations** — create or update multiple transactions in a single call
- **Dollar amounts** — accepts dollars in parameters, converts to YNAB milliunits internally
- **Token in the OS credential store** — not in a config file any agent can read
- **Human confirmation for every write** — with a real before/after diff, read live from YNAB
- **Encrypted cache** — cached budget data is AES-256-GCM at rest

## Quick Start

Store your [YNAB personal access token](https://app.ynab.com/settings/developer)
once, in your OS credential store:

```bash
uv tool run mcp-ynab auth login
```

The token is read hidden, validated against the YNAB API, and then saved to
Windows Credential Manager, macOS Keychain, or Secret Service. It does not go
into any config file, and it is not read from `argv` or left in shell history.

Nothing appears as you type or paste — that is intended. If your terminal will
not paste into a hidden prompt (the Windows console sends Ctrl+V as a control
character rather than pasting), feed it from a file instead:

```bash
uv tool run mcp-ynab auth login --stdin < token.txt
```

```bash
uv tool run mcp-ynab auth status   # which source is in use, plus a fingerprint
uv tool run mcp-ynab auth logout   # remove the stored token
uv tool run mcp-ynab cache purge   # delete the local cache and its encryption key
```

## Configuration

No API key goes in the config — `auth login` already stored it.

### Claude Desktop / ChatGPT

Add to your config file:

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["tool", "run", "mcp-ynab"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add-json ynab --scope user '{"type":"stdio","command":"uv","args":["tool","run","mcp-ynab"]}'
```

See [mcp-ynab.com](https://mcp-ynab.com) for config file locations and troubleshooting.

### Environment variables

| Variable | Default | Effect |
|---|---|---|
| `YNAB_API_KEY` | unset | Still honoured, with a deprecation warning on stderr. Putting it in an MCP client config writes your token in plaintext into a file any agent can read — prefer `auth login`. |
| `YNAB_ALLOW_ENV_KEY` | `1` | Set to `0` to refuse `YNAB_API_KEY` entirely, so the credential store is the only accepted source. |
| `YNAB_READ_ONLY` | `0` | Set to `1` to stop the 16 write tools being registered at all. They never reach the model's tool list. |
| `YNAB_CACHE_ENCRYPTION` | `1` | Set to `0` to store the cache in plaintext. Debugging only. |

## Writes require your confirmation

Every tool that changes something in YNAB asks you first, showing the current
state read live from the YNAB API alongside exactly what would change:

```
CONFIRM: Update transaction
Plan: bud-1

Current state, read from the YNAB API just now:
  2026-03-15  Chez Nowhere  Groceries  -$50.25  cleared=uncleared  approved=no

This will change:
  amount   : -$50.25 -> -$60.00
  approved : no -> yes

Confirm to apply exactly this. Nothing else will be sent.
```

Bulk operations list every row rather than summarising a count. Declining, or a
client that cannot ask you, blocks the write — there is no fallback that applies
it unconfirmed.

This relies on your MCP client supporting elicitation. **On a client that does
not, writes will refuse outright.** See [SECURITY.md](./SECURITY.md) for the full
threat model, including what the credential store does and does not protect
against.

## Available Tools

| Group | Tools |
|-------|-------|
| **User** | `get_user` |
| **Plans** | `list_plans`, `get_plan`, `get_plan_settings` |
| **Accounts** | `list_accounts`, `get_account`, `create_account` |
| **Categories** | `list_categories`, `get_category`, `create_category`, `update_category`, `create_category_group`, `update_category_group`, `get_category_for_month`, `update_category_for_month` |
| **Payees** | `list_payees`, `get_payee`, `update_payee` |
| **Payee Locations** | `list_payee_locations`, `get_payee_location`, `get_payee_locations_by_payee` |
| **Months** | `list_months`, `get_month` |
| **Money Movements** | `list_money_movements`, `get_money_movements_for_month`, `list_money_movement_groups`, `get_money_movement_groups_for_month` |
| **Transactions** | `list_transactions`, `get_transaction`, `get_transactions_by_account`, `get_transactions_by_category`, `get_transactions_by_month`, `get_transactions_by_payee`, `search_transactions`, `create_transaction`, `create_transactions`, `update_transaction`, `update_transactions`, `delete_transaction`, `import_transactions` |
| **Scheduled** | `list_scheduled_transactions`, `get_scheduled_transaction`, `create_scheduled_transaction`, `update_scheduled_transaction`, `delete_scheduled_transaction` |
| **Analytics** | `get_money_flow`, `get_spending_by_category` |

### Field selection

Every tool that returns a model accepts an optional `exclude_fields` list. By
default each tool returns a sensible subset of fields to keep token usage low.
See [FIELDS.md](./FIELDS.md) for per-model defaults and override examples.

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Fresh-resolution smoke test (resolves from pyproject.toml, not uv.lock)
python scripts/smoke_test.py

# Run server standalone
uv run python -m src.server
```

Running the server needs a token: `uv run python -m src.cli auth login`, or
`YNAB_API_KEY` in `.env.local`.

## License

[AGPL-3.0](LICENSE)

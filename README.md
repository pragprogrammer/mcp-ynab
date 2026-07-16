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

## Quick Start

```
uv tool run mcp-ynab
```

Requires a [YNAB personal access token](https://app.ynab.com/settings/developer) set as `YNAB_API_KEY`.

## Configuration

### Claude Desktop / ChatGPT

Add to your config file:

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["tool", "run", "mcp-ynab"],
      "env": {
        "YNAB_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add-json ynab --scope user '{"type":"stdio","command":"uv","args":["tool","run","mcp-ynab"],"env":{"YNAB_API_KEY":"your-api-key-here"}}'
```

See [mcp-ynab.com](https://mcp-ynab.com) for config file locations and troubleshooting.

## Available Tools

| Group | Tools |
|-------|-------|
| **User** | `get_user` |
| **Plans** | `list_plans`, `get_plan`, `get_plan_settings` |
| **Accounts** | `list_accounts`, `get_account`, `create_account` |
| **Categories** | `list_categories`, `get_category`, `create_category`, `update_category`, `create_category_group`, `update_category_group`, `get_category_for_month`, `update_category_for_month` |
| **Payees** | `list_payees`, `get_payee`, `create_payee`, `update_payee` |
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

# Run server standalone
uv run python -m src.server
```

Requires `YNAB_API_KEY` in `.env.local` for running the server.

## License

[AGPL-3.0](LICENSE)

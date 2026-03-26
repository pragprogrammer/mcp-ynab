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
| **Budget** | `list_budgets`, `get_budget` |
| **Accounts** | `list_accounts`, `get_account` |
| **Transactions** | `list_transactions`, `get_transaction`, `get_transactions_by_account`, `get_transactions_by_category`, `get_transactions_by_payee`, `search_transactions`, `create_transaction`, `create_transactions`, `update_transaction`, `update_transactions`, `delete_transaction` |
| **Categories** | `list_categories`, `get_category_for_month`, `update_category_budget` |
| **Payees** | `list_payees` |
| **Months** | `list_months`, `get_month` |
| **Scheduled** | `list_scheduled_transactions` |
| **Analytics** | `get_money_flow`, `get_spending_by_category` |

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

# Next Steps

## Publish MCP server to PyPI
- Add entry point to `pyproject.toml` so `uvx ynab-mcp` works
- Choose package name (e.g. `ynab-mcp`) and verify availability on PyPI
- Add `[project.scripts]` with `ynab-mcp = "src.server:main"`
- Test local install with `uvx --from . ynab-mcp`
- Publish to PyPI

## Landing page polish
- Add a favicon (YNAB-themed or custom)
- Add a donate link/button (GitHub Sponsors, Buy Me a Coffee, etc.)
- Consider adding an OG image for social sharing
- Wire up Vercel deploy for the `website/` directory (update build settings)

## Repo cleanup
- Rename repo from BudgetLens to something like `ynab-mcp` to match the package
- Update all GitHub links in the landing page after rename
- Write a proper README.md

## Distribution
- Post to r/ynab subreddit
- Consider adding to the MCP server directory (https://github.com/modelcontextprotocol/servers)

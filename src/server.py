import json
import sys
from datetime import date
from functools import wraps

import httpx
from mcp.server.fastmcp import FastMCP

from src.cache.service import CacheService
from src.config import Settings
from src.db.engine import init_db
from src.models.account import ACCOUNT_DISPLAY_EXCLUDE
from src.models.budget import BUDGET_SUMMARY_DISPLAY_EXCLUDE
from src.models.category import CATEGORY_DETAIL_INCLUDE, CATEGORY_LIST_EXCLUDE
from src.models.month import MONTH_DISPLAY_EXCLUDE
from src.models.payee import PAYEE_DISPLAY_EXCLUDE
from src.models.transaction import SCHEDULED_TRANSACTION_DISPLAY_EXCLUDE, TRANSACTION_DISPLAY_EXCLUDE
from src.ynab_client import YNABClient, YNABError

try:
    settings = Settings()  # type: ignore[call-arg]
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP("ynab")
client = YNABClient(settings.ynab_api_key, timeout=settings.http_timeout)
cache = CacheService(client, settings)

_db_initialized = False


async def _ensure_db():
    global _db_initialized
    if not _db_initialized:
        await init_db(settings.cache_db_path)
        _db_initialized = True


def handle_errors(func):
    """Decorator that catches YNAB and HTTP errors and returns friendly messages."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            await _ensure_db()
            return await func(*args, **kwargs)
        except YNABError as e:
            return json.dumps({"error": e.message, "error_id": e.error_id, "status_code": e.status_code})
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
        except httpx.RequestError as e:
            return json.dumps({"error": f"Request failed: {e}"})

    return wrapper


# ── Budget Tools ─────────────────────────────────────────────


@mcp.tool()
@handle_errors
async def list_budgets() -> str:
    """List all budgets in the user's YNAB account. Call this first to get budget IDs."""
    budgets = await cache.get_budgets()
    result = [b.model_dump(by_alias=True, exclude=BUDGET_SUMMARY_DISPLAY_EXCLUDE) for b in budgets]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_budget(budget_id: str) -> str:
    """Get details for a specific budget.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    budget = await cache.get_budget(budget_id)
    return json.dumps(budget.model_dump(by_alias=True), indent=2)


# ── Account Tools ────────────────────────────────────────────


@mcp.tool()
@handle_errors
async def list_accounts(budget_id: str) -> str:
    """List all accounts in a budget.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    accounts = await cache.get_accounts(budget_id)
    result = [a.model_dump(by_alias=True, exclude=ACCOUNT_DISPLAY_EXCLUDE) for a in accounts]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_account(account_id: str, budget_id: str) -> str:
    """Get details for a specific account.

    Args:
        account_id: The account ID
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    account = await cache.get_account(account_id, budget_id)
    return json.dumps(account.model_dump(by_alias=True, exclude=ACCOUNT_DISPLAY_EXCLUDE), indent=2)


# ── Transaction Tools ────────────────────────────────────────


@mcp.tool()
@handle_errors
async def list_transactions(
    budget_id: str,
    since_date: str | None = None,
    type: str | None = None,
) -> str:
    """List transactions in a budget. Can filter by date and type.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
        type: Filter by 'uncategorized' or 'unapproved'
    """
    transactions = await cache.get_transactions(budget_id, since_date, type)
    result = [t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE) for t in transactions]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_transaction(transaction_id: str, budget_id: str) -> str:
    """Get a specific transaction by ID.

    Args:
        transaction_id: The transaction ID
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    txn = await cache.get_transaction(transaction_id, budget_id)
    return json.dumps(txn.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE), indent=2)


@mcp.tool()
@handle_errors
async def get_transactions_by_account(
    account_id: str,
    budget_id: str,
    since_date: str | None = None,
) -> str:
    """Get transactions for a specific account.

    Args:
        account_id: The account ID
        budget_id: The budget ID (use list_budgets to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
    """
    transactions = await cache.get_transactions_by_account(account_id, budget_id, since_date)
    result = [t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE) for t in transactions]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_transactions_by_category(
    category_id: str,
    budget_id: str,
    since_date: str | None = None,
) -> str:
    """Get transactions for a specific category.

    Args:
        category_id: The category ID
        budget_id: The budget ID (use list_budgets to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
    """
    transactions = await cache.get_transactions_by_category(category_id, budget_id, since_date)
    result = [t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE) for t in transactions]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_transactions_by_payee(
    payee_id: str,
    budget_id: str,
    since_date: str | None = None,
) -> str:
    """Get transactions for a specific payee.

    Args:
        payee_id: The payee ID
        budget_id: The budget ID (use list_budgets to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
    """
    transactions = await cache.get_transactions_by_payee(payee_id, budget_id, since_date)
    result = [t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE) for t in transactions]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def create_transaction(
    budget_id: str,
    account_id: str,
    date: str,
    amount: float,
    payee_name: str | None = None,
    category_id: str | None = None,
    memo: str | None = None,
    cleared: str = "uncleared",
    approved: bool = False,
) -> str:
    """Create a new transaction.

    Args:
        account_id: The account ID for this transaction
        date: Transaction date in YYYY-MM-DD format
        amount: Amount in dollars (negative for outflow, positive for inflow). e.g. -50.25 for spending $50.25
        payee_name: Name of the payee
        category_id: Category ID to assign
        memo: Optional memo/note
        cleared: 'cleared', 'uncleared', or 'reconciled'
        approved: Whether the transaction is approved
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    transaction = {
        "account_id": account_id,
        "date": date,
        "amount": int(amount * 1000),  # Convert dollars to milliunits
        "cleared": cleared,
        "approved": approved,
    }
    if payee_name:
        transaction["payee_name"] = payee_name
    if category_id:
        transaction["category_id"] = category_id
    if memo:
        transaction["memo"] = memo

    txn = await cache.create_transaction(transaction, budget_id)
    return json.dumps(txn.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE), indent=2)


@mcp.tool()
@handle_errors
async def create_transactions(
    budget_id: str,
    account_id: str,
    transactions: list[dict],
) -> str:
    """Create multiple transactions in a single API call. Ideal for bulk imports.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
        account_id: Default account ID for all transactions
        transactions: List of transaction dicts, each with:
            - date: Transaction date in YYYY-MM-DD format
            - amount: Amount in dollars (negative for outflow, positive for inflow)
            - payee_name: (optional) Name of the payee
            - category_id: (optional) Category ID to assign
            - memo: (optional) Memo/note
            - account_id: (optional) Override the default account ID
            - cleared: (optional) 'cleared', 'uncleared', or 'reconciled' (default: 'uncleared')
            - approved: (optional) Whether the transaction is approved (default: false)
    """
    prepared = []
    for txn_input in transactions:
        txn = {
            "account_id": txn_input.get("account_id", account_id),
            "date": txn_input["date"],
            "amount": int(txn_input["amount"] * 1000),
            "cleared": txn_input.get("cleared", "uncleared"),
            "approved": txn_input.get("approved", False),
        }
        if txn_input.get("payee_name"):
            txn["payee_name"] = txn_input["payee_name"]
        if txn_input.get("category_id"):
            txn["category_id"] = txn_input["category_id"]
        if txn_input.get("memo"):
            txn["memo"] = txn_input["memo"]
        prepared.append(txn)

    txns = await cache.create_transactions(prepared, budget_id)
    result = [t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE) for t in txns]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def update_transaction(
    budget_id: str,
    transaction_id: str,
    account_id: str | None = None,
    date: str | None = None,
    amount: float | None = None,
    payee_name: str | None = None,
    category_id: str | None = None,
    memo: str | None = None,
    cleared: str | None = None,
    approved: bool | None = None,
) -> str:
    """Update an existing transaction. Only provide the fields you want to change.

    Args:
        transaction_id: The transaction ID to update
        account_id: New account ID
        date: New date (YYYY-MM-DD)
        amount: New amount in dollars (negative for outflow, positive for inflow)
        payee_name: New payee name
        category_id: New category ID
        memo: New memo
        cleared: 'cleared', 'uncleared', or 'reconciled'
        approved: Whether the transaction is approved
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    transaction = {}
    if account_id is not None:
        transaction["account_id"] = account_id
    if date is not None:
        transaction["date"] = date
    if amount is not None:
        transaction["amount"] = int(amount * 1000)
    if payee_name is not None:
        transaction["payee_name"] = payee_name
    if category_id is not None:
        transaction["category_id"] = category_id
    if memo is not None:
        transaction["memo"] = memo
    if cleared is not None:
        transaction["cleared"] = cleared
    if approved is not None:
        transaction["approved"] = approved

    txn = await cache.update_transaction(transaction_id, transaction, budget_id)
    return json.dumps(txn.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE), indent=2)


@mcp.tool()
@handle_errors
async def delete_transaction(transaction_id: str, budget_id: str) -> str:
    """Delete a transaction.

    Args:
        transaction_id: The transaction ID to delete
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    txn = await cache.delete_transaction(transaction_id, budget_id)
    return json.dumps(txn.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE), indent=2)


@mcp.tool()
@handle_errors
async def update_transactions(
    budget_id: str,
    transactions: list[dict],
) -> str:
    """Update multiple transactions in a single API call. Each transaction must include its ID.

    Only provided fields are updated (sparse update). Ideal for bulk recategorization,
    bulk approval, bulk clearing, etc.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
        transactions: List of transaction dicts, each requiring:
            - id: The transaction ID to update
            And optionally:
            - account_id: New account ID
            - date: New date (YYYY-MM-DD)
            - amount: New amount in dollars (negative for outflow, positive for inflow)
            - payee_name: New payee name
            - category_id: New category ID
            - memo: New memo
            - cleared: 'cleared', 'uncleared', or 'reconciled'
            - approved: Whether the transaction is approved
            - flag_color: Flag color ('red', 'orange', 'yellow', 'green', 'blue', 'purple', or null)
    """
    prepared = []
    for txn_input in transactions:
        if "id" not in txn_input:
            return json.dumps({"error": "Each transaction must include an 'id' field"})
        txn: dict = {"id": txn_input["id"]}
        if "account_id" in txn_input:
            txn["account_id"] = txn_input["account_id"]
        if "date" in txn_input:
            txn["date"] = txn_input["date"]
        if "amount" in txn_input:
            txn["amount"] = int(txn_input["amount"] * 1000)
        if "payee_name" in txn_input:
            txn["payee_name"] = txn_input["payee_name"]
        if "category_id" in txn_input:
            txn["category_id"] = txn_input["category_id"]
        if "memo" in txn_input:
            txn["memo"] = txn_input["memo"]
        if "cleared" in txn_input:
            txn["cleared"] = txn_input["cleared"]
        if "approved" in txn_input:
            txn["approved"] = txn_input["approved"]
        if "flag_color" in txn_input:
            txn["flag_color"] = txn_input["flag_color"]
        prepared.append(txn)

    txns = await cache.update_transactions(prepared, budget_id)
    result = [t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE) for t in txns]
    return json.dumps(result, indent=2)


# ── Category Tools ───────────────────────────────────────────


@mcp.tool()
@handle_errors
async def list_categories(budget_id: str) -> str:
    """List all categories grouped by category group.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    groups = await cache.get_categories(budget_id)
    result = []
    for g in groups:
        gd = g.model_dump(by_alias=True, exclude={"deleted"})
        gd["categories"] = [
            c.model_dump(by_alias=True, exclude=CATEGORY_LIST_EXCLUDE) for c in g.categories
        ]
        result.append(gd)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_category_for_month(
    category_id: str, month: str, budget_id: str
) -> str:
    """Get category details for a specific month.

    Args:
        category_id: The category ID
        month: Month in YYYY-MM-DD format (use first of month, e.g. '2026-03-01')
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    cat = await cache.get_category_for_month(month, category_id, budget_id)
    return json.dumps(cat.model_dump(by_alias=True, include=CATEGORY_DETAIL_INCLUDE), indent=2)


@mcp.tool()
@handle_errors
async def update_category_budget(
    category_id: str, month: str, budgeted: float, budget_id: str
) -> str:
    """Update the budgeted amount for a category in a specific month.

    Args:
        category_id: The category ID
        month: Month in YYYY-MM-DD format (use first of month, e.g. '2026-03-01')
        budgeted: Budgeted amount in dollars (e.g. 500.00)
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    cat = await cache.update_category_budget(
        month, category_id, int(budgeted * 1000), budget_id
    )
    return json.dumps(cat.model_dump(by_alias=True, exclude=CATEGORY_LIST_EXCLUDE | {"hidden"}), indent=2)


# ── Payee Tools ──────────────────────────────────────────────


@mcp.tool()
@handle_errors
async def list_payees(budget_id: str) -> str:
    """List all payees in a budget.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    payees = await cache.get_payees(budget_id)
    result = [p.model_dump(by_alias=True, exclude=PAYEE_DISPLAY_EXCLUDE) for p in payees]
    return json.dumps(result, indent=2)


# ── Month Tools ──────────────────────────────────────────────


@mcp.tool()
@handle_errors
async def list_months(budget_id: str) -> str:
    """List all budget months.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    months = await cache.get_months(budget_id)
    result = [m.model_dump(by_alias=True, exclude=MONTH_DISPLAY_EXCLUDE) for m in months]
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors
async def get_month(month: str, budget_id: str) -> str:
    """Get detailed budget month summary including all categories. Use 'current' for the current month.

    Args:
        month: Month in YYYY-MM-DD format (first of month) or 'current'
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    m = await cache.get_month(month, budget_id)
    md = m.model_dump(by_alias=True, exclude=MONTH_DISPLAY_EXCLUDE)
    md["categories"] = [
        c.model_dump(by_alias=True, exclude=CATEGORY_LIST_EXCLUDE | {"hidden"})
        for c in m.categories
    ]
    return json.dumps(md, indent=2)


# ── Scheduled Transaction Tools ──────────────────────────────


@mcp.tool()
@handle_errors
async def list_scheduled_transactions(budget_id: str) -> str:
    """List all scheduled (recurring) transactions.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
    """
    transactions = await cache.get_scheduled_transactions(budget_id)
    result = [t.model_dump(by_alias=True, exclude=SCHEDULED_TRANSACTION_DISPLAY_EXCLUDE) for t in transactions]
    return json.dumps(result, indent=2)


# ── Analytics Tools ──────────────────────────────────────────


MONEY_FLOW_EXCLUDE_GROUPS = {"Internal Master Category", "Credit Card Payments"}


@mcp.tool()
@handle_errors
async def get_money_flow(budget_id: str, month: str = "current") -> str:
    """Build Sankey chart data showing money flow from income sources to spending category groups.

    Returns nodes and index-based links suitable for Sankey/flow visualizations.

    Args:
        budget_id: The budget ID (use list_budgets to find available IDs)
        month: Month in YYYY-MM-DD format (first of month, e.g. '2026-03-01') or 'current'
    """
    if month == "current":
        today = date.today()
        month = today.replace(day=1).strftime("%Y-%m-%d")

    # Fetch month detail (has categories with activity and income total)
    month_detail = await cache.get_month(month, budget_id)

    # Group categories by category_group_name and sum activity
    group_activity: dict[str, int] = {}
    for cat in month_detail.categories:
        group_name = cat.category_group_name or "Uncategorized"
        if group_name in MONEY_FLOW_EXCLUDE_GROUPS:
            continue
        group_activity[group_name] = group_activity.get(group_name, 0) + cat.activity

    # Filter out groups with zero activity
    group_activity = {name: activity for name, activity in group_activity.items() if activity != 0}

    # Build nodes: index 0 is Income, then one per category group
    nodes = [{"name": "Income"}]
    links = []
    total_spent = 0.0

    for group_name, activity_milliunits in sorted(group_activity.items()):
        value = abs(activity_milliunits) / 1000.0
        total_spent += value
        target_index = len(nodes)
        nodes.append({"name": group_name})
        links.append({"source": 0, "target": target_index, "value": round(value, 2)})

    total_income = abs(month_detail.income) / 1000.0

    result = {
        "month": month,
        "total_income": round(total_income, 2),
        "total_spent": round(total_spent, 2),
        "nodes": nodes,
        "links": links,
    }
    return json.dumps(result, indent=2)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Tests for MCP server tools.

Tests each tool by mocking the CacheService so no real YNAB API calls are made.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.models import (
    Account,
    BudgetDetail,
    BudgetSummary,
    Category,
    CategoryGroup,
    MonthDetail,
    MonthSummary,
    Payee,
    ScheduledTransaction,
    Transaction,
)


# ── Fixtures ──────────────────────────────────────────────────


def _make_transaction(**overrides) -> Transaction:
    defaults = {"id": "txn-1", "date": "2026-03-15", "amount": -50250}
    return Transaction(**{**defaults, **overrides})


def _make_account(**overrides) -> Account:
    defaults = {"id": "acc-1", "name": "Checking", "type": "checking"}
    return Account(**{**defaults, **overrides})


def _make_budget_summary(**overrides) -> BudgetSummary:
    defaults = {"id": "bud-1", "name": "My Budget", "last_modified_on": "2026-03-15"}
    return BudgetSummary(**{**defaults, **overrides})


def _make_budget_detail(**overrides) -> BudgetDetail:
    defaults = {"id": "bud-1", "name": "My Budget", "last_modified_on": "2026-03-15"}
    return BudgetDetail(**{**defaults, **overrides})


def _make_category(**overrides) -> Category:
    defaults = {"id": "cat-1", "category_group_id": "grp-1", "name": "Food"}
    return Category(**{**defaults, **overrides})


def _make_category_group(**overrides) -> CategoryGroup:
    defaults = {"id": "grp-1", "name": "Bills"}
    return CategoryGroup(**{**defaults, **overrides})


def _make_payee(**overrides) -> Payee:
    defaults = {"id": "pay-1", "name": "Amazon"}
    return Payee(**{**defaults, **overrides})


def _make_month_summary(**overrides) -> MonthSummary:
    defaults = {"month": "2026-03-01", "income": 5000000}
    return MonthSummary(**{**defaults, **overrides})


def _make_month_detail(**overrides) -> MonthDetail:
    cats = overrides.pop("categories", [_make_category()])
    defaults = {"month": "2026-03-01", "income": 5000000, "categories": cats}
    return MonthDetail(**{**defaults, **overrides})


def _make_scheduled_transaction(**overrides) -> ScheduledTransaction:
    defaults = {"id": "st-1", "date_next": "2026-04-01", "frequency": "monthly", "amount": -10000}
    return ScheduledTransaction(**{**defaults, **overrides})


# We need to patch the module-level objects in server.py.
# The server module creates `cache` and `client` at import time,
# so we patch `src.server.cache` (the CacheService instance).

CACHE_PATH = "src.server.cache"
DB_PATH = "src.server._ensure_db"


@pytest.fixture
def mock_cache():
    with patch(CACHE_PATH) as mock, patch(DB_PATH, new_callable=AsyncMock):
        yield mock


# ── Budget Tools ──────────────────────────────────────────────


class TestListBudgets:
    @pytest.mark.asyncio
    async def test_returns_budgets(self, mock_cache):
        from src.server import list_budgets

        mock_cache.get_budgets = AsyncMock(return_value=[_make_budget_summary()])
        result = json.loads(await list_budgets())
        assert len(result) == 1
        assert result[0]["id"] == "bud-1"
        assert result[0]["name"] == "My Budget"

    @pytest.mark.asyncio
    async def test_empty_budgets(self, mock_cache):
        from src.server import list_budgets

        mock_cache.get_budgets = AsyncMock(return_value=[])
        result = json.loads(await list_budgets())
        assert result == []


class TestGetBudget:
    @pytest.mark.asyncio
    async def test_returns_budget_detail(self, mock_cache):
        from src.server import get_budget

        mock_cache.get_budget = AsyncMock(return_value=_make_budget_detail())
        result = json.loads(await get_budget(budget_id="bud-1"))
        assert result["id"] == "bud-1"
        assert result["last_modified"] == "2026-03-15"


# ── Account Tools ─────────────────────────────────────────────


class TestListAccounts:
    @pytest.mark.asyncio
    async def test_returns_accounts(self, mock_cache):
        from src.server import list_accounts

        mock_cache.get_accounts = AsyncMock(return_value=[_make_account()])
        result = json.loads(await list_accounts(budget_id="bud-1"))
        assert len(result) == 1
        assert result[0]["name"] == "Checking"
        assert "deleted" not in result[0]


class TestGetAccount:
    @pytest.mark.asyncio
    async def test_returns_single_account(self, mock_cache):
        from src.server import get_account

        mock_cache.get_account = AsyncMock(return_value=_make_account())
        result = json.loads(await get_account(account_id="acc-1", budget_id="bud-1"))
        assert result["id"] == "acc-1"


# ── Transaction Tools ─────────────────────────────────────────


class TestListTransactions:
    @pytest.mark.asyncio
    async def test_returns_transactions(self, mock_cache):
        from src.server import list_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await list_transactions(budget_id="bud-1"))
        assert len(result) == 1
        assert result[0]["amount"] == -50250

    @pytest.mark.asyncio
    async def test_passes_filters(self, mock_cache):
        from src.server import list_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[])
        await list_transactions(budget_id="bud-1", since_date="2026-01-01", type="uncategorized")
        mock_cache.get_transactions.assert_called_once_with("bud-1", "2026-01-01", "uncategorized")


class TestGetTransaction:
    @pytest.mark.asyncio
    async def test_returns_single_transaction(self, mock_cache):
        from src.server import get_transaction

        mock_cache.get_transaction = AsyncMock(return_value=_make_transaction())
        result = json.loads(await get_transaction(transaction_id="txn-1", budget_id="bud-1"))
        assert result["id"] == "txn-1"


class TestGetTransactionsByAccount:
    @pytest.mark.asyncio
    async def test_returns_filtered_transactions(self, mock_cache):
        from src.server import get_transactions_by_account

        mock_cache.get_transactions_by_account = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await get_transactions_by_account(account_id="acc-1", budget_id="bud-1"))
        assert len(result) == 1


class TestGetTransactionsByCategory:
    @pytest.mark.asyncio
    async def test_returns_filtered_transactions(self, mock_cache):
        from src.server import get_transactions_by_category

        mock_cache.get_transactions_by_category = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await get_transactions_by_category(category_id="cat-1", budget_id="bud-1"))
        assert len(result) == 1


class TestGetTransactionsByPayee:
    @pytest.mark.asyncio
    async def test_returns_filtered_transactions(self, mock_cache):
        from src.server import get_transactions_by_payee

        mock_cache.get_transactions_by_payee = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await get_transactions_by_payee(payee_id="pay-1", budget_id="bud-1"))
        assert len(result) == 1


class TestCreateTransaction:
    @pytest.mark.asyncio
    async def test_converts_dollars_to_milliunits(self, mock_cache):
        from src.server import create_transaction

        mock_cache.create_transaction = AsyncMock(return_value=_make_transaction(amount=-50250))
        await create_transaction(
            budget_id="bud-1", account_id="acc-1", date="2026-03-15", amount=-50.25,
        )
        call_args = mock_cache.create_transaction.call_args
        txn_dict = call_args[0][0]
        assert txn_dict["amount"] == -50250

    @pytest.mark.asyncio
    async def test_includes_optional_fields(self, mock_cache):
        from src.server import create_transaction

        mock_cache.create_transaction = AsyncMock(return_value=_make_transaction())
        await create_transaction(
            budget_id="bud-1", account_id="acc-1", date="2026-03-15", amount=-10.0,
            payee_name="Store", category_id="cat-1", memo="test",
        )
        txn_dict = mock_cache.create_transaction.call_args[0][0]
        assert txn_dict["payee_name"] == "Store"
        assert txn_dict["category_id"] == "cat-1"
        assert txn_dict["memo"] == "test"

    @pytest.mark.asyncio
    async def test_omits_none_optional_fields(self, mock_cache):
        from src.server import create_transaction

        mock_cache.create_transaction = AsyncMock(return_value=_make_transaction())
        await create_transaction(
            budget_id="bud-1", account_id="acc-1", date="2026-03-15", amount=-10.0,
        )
        txn_dict = mock_cache.create_transaction.call_args[0][0]
        assert "payee_name" not in txn_dict
        assert "category_id" not in txn_dict
        assert "memo" not in txn_dict


class TestCreateTransactions:
    @pytest.mark.asyncio
    async def test_converts_all_amounts(self, mock_cache):
        from src.server import create_transactions

        mock_cache.create_transactions = AsyncMock(
            return_value=[_make_transaction(id="t1"), _make_transaction(id="t2")]
        )
        await create_transactions(
            budget_id="bud-1",
            account_id="acc-1",
            transactions=[
                {"date": "2026-03-15", "amount": -25.50},
                {"date": "2026-03-16", "amount": -10.00, "payee_name": "Cafe"},
            ],
        )
        prepared = mock_cache.create_transactions.call_args[0][0]
        assert prepared[0]["amount"] == -25500
        assert prepared[1]["amount"] == -10000
        assert prepared[1]["payee_name"] == "Cafe"

    @pytest.mark.asyncio
    async def test_per_transaction_account_override(self, mock_cache):
        from src.server import create_transactions

        mock_cache.create_transactions = AsyncMock(return_value=[_make_transaction()])
        await create_transactions(
            budget_id="bud-1",
            account_id="acc-default",
            transactions=[{"date": "2026-03-15", "amount": -5.0, "account_id": "acc-override"}],
        )
        prepared = mock_cache.create_transactions.call_args[0][0]
        assert prepared[0]["account_id"] == "acc-override"

    @pytest.mark.asyncio
    async def test_uses_default_account_id(self, mock_cache):
        from src.server import create_transactions

        mock_cache.create_transactions = AsyncMock(return_value=[_make_transaction()])
        await create_transactions(
            budget_id="bud-1",
            account_id="acc-default",
            transactions=[{"date": "2026-03-15", "amount": -5.0}],
        )
        prepared = mock_cache.create_transactions.call_args[0][0]
        assert prepared[0]["account_id"] == "acc-default"


class TestUpdateTransaction:
    @pytest.mark.asyncio
    async def test_converts_amount_to_milliunits(self, mock_cache):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock(return_value=_make_transaction())
        await update_transaction(budget_id="bud-1", transaction_id="txn-1", amount=-75.00)
        call_args = mock_cache.update_transaction.call_args
        txn_dict = call_args[0][1]
        assert txn_dict["amount"] == -75000

    @pytest.mark.asyncio
    async def test_only_includes_provided_fields(self, mock_cache):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock(return_value=_make_transaction())
        await update_transaction(budget_id="bud-1", transaction_id="txn-1", memo="updated")
        txn_dict = mock_cache.update_transaction.call_args[0][1]
        assert txn_dict == {"memo": "updated"}


class TestDeleteTransaction:
    @pytest.mark.asyncio
    async def test_deletes_and_returns(self, mock_cache):
        from src.server import delete_transaction

        mock_cache.delete_transaction = AsyncMock(return_value=_make_transaction())
        result = json.loads(await delete_transaction(transaction_id="txn-1", budget_id="bud-1"))
        assert result["id"] == "txn-1"


# ── Category Tools ────────────────────────────────────────────


class TestListCategories:
    @pytest.mark.asyncio
    async def test_returns_grouped_categories(self, mock_cache):
        from src.server import list_categories

        cat = _make_category()
        group = _make_category_group(categories=[cat])
        mock_cache.get_categories = AsyncMock(return_value=[group])
        result = json.loads(await list_categories(budget_id="bud-1"))
        assert len(result) == 1
        assert result[0]["name"] == "Bills"
        assert len(result[0]["categories"]) == 1


class TestGetCategoryForMonth:
    @pytest.mark.asyncio
    async def test_returns_category_with_goals(self, mock_cache):
        from src.server import get_category_for_month

        cat = _make_category(goal_type="TB", goal_target=500000, budgeted=250000)
        mock_cache.get_category_for_month = AsyncMock(return_value=cat)
        result = json.loads(await get_category_for_month(
            category_id="cat-1", month="2026-03-01", budget_id="bud-1"
        ))
        assert result["goal_type"] == "TB"


class TestUpdateCategoryBudget:
    @pytest.mark.asyncio
    async def test_converts_dollars_to_milliunits(self, mock_cache):
        from src.server import update_category_budget

        mock_cache.update_category_budget = AsyncMock(return_value=_make_category(budgeted=500000))
        await update_category_budget(
            category_id="cat-1", month="2026-03-01", budgeted=500.00, budget_id="bud-1"
        )
        call_args = mock_cache.update_category_budget.call_args
        assert call_args[0][2] == 500000  # third positional arg is budgeted in milliunits


# ── Payee Tools ───────────────────────────────────────────────


class TestListPayees:
    @pytest.mark.asyncio
    async def test_returns_payees(self, mock_cache):
        from src.server import list_payees

        mock_cache.get_payees = AsyncMock(return_value=[_make_payee()])
        result = json.loads(await list_payees(budget_id="bud-1"))
        assert len(result) == 1
        assert result[0]["name"] == "Amazon"


# ── Month Tools ───────────────────────────────────────────────


class TestListMonths:
    @pytest.mark.asyncio
    async def test_returns_months(self, mock_cache):
        from src.server import list_months

        mock_cache.get_months = AsyncMock(return_value=[_make_month_summary()])
        result = json.loads(await list_months(budget_id="bud-1"))
        assert len(result) == 1
        assert result[0]["income"] == 5000000


class TestGetMonth:
    @pytest.mark.asyncio
    async def test_returns_month_with_categories(self, mock_cache):
        from src.server import get_month

        mock_cache.get_month = AsyncMock(return_value=_make_month_detail())
        result = json.loads(await get_month(month="2026-03-01", budget_id="bud-1"))
        assert "categories" in result
        assert result["income"] == 5000000


# ── Scheduled Transactions ────────────────────────────────────


class TestListScheduledTransactions:
    @pytest.mark.asyncio
    async def test_returns_scheduled(self, mock_cache):
        from src.server import list_scheduled_transactions

        mock_cache.get_scheduled_transactions = AsyncMock(
            return_value=[_make_scheduled_transaction()]
        )
        result = json.loads(await list_scheduled_transactions(budget_id="bud-1"))
        assert len(result) == 1
        assert result[0]["frequency"] == "monthly"


# ── Analytics (Money Flow) ────────────────────────────────────


class TestGetMoneyFlow:
    @pytest.mark.asyncio
    async def test_builds_sankey_data(self, mock_cache):
        from src.server import get_money_flow

        cats = [
            _make_category(name="Rent", category_group_name="Housing", activity=-1500000),
            _make_category(name="Food", category_group_name="Groceries", activity=-500000),
        ]
        month = _make_month_detail(income=3000000, categories=cats)
        mock_cache.get_month = AsyncMock(return_value=month)

        result = json.loads(await get_money_flow(budget_id="bud-1", month="2026-03-01"))
        assert result["total_income"] == 3000.0
        assert result["total_spent"] == 2000.0
        assert len(result["nodes"]) == 3  # Income + 2 groups
        assert len(result["links"]) == 2

    @pytest.mark.asyncio
    async def test_excludes_internal_and_credit_card_groups(self, mock_cache):
        from src.server import get_money_flow

        cats = [
            _make_category(name="Rent", category_group_name="Housing", activity=-1000000),
            _make_category(name="Transfer", category_group_name="Internal Master Category", activity=-500000),
            _make_category(name="CC Payment", category_group_name="Credit Card Payments", activity=-200000),
        ]
        month = _make_month_detail(income=2000000, categories=cats)
        mock_cache.get_month = AsyncMock(return_value=month)

        result = json.loads(await get_money_flow(budget_id="bud-1", month="2026-03-01"))
        node_names = [n["name"] for n in result["nodes"]]
        assert "Internal Master Category" not in node_names
        assert "Credit Card Payments" not in node_names
        assert "Housing" in node_names
        assert result["total_spent"] == 1000.0

    @pytest.mark.asyncio
    async def test_skips_zero_activity_groups(self, mock_cache):
        from src.server import get_money_flow

        cats = [
            _make_category(name="Rent", category_group_name="Housing", activity=-1000000),
            _make_category(name="Unused", category_group_name="Entertainment", activity=0),
        ]
        month = _make_month_detail(income=1000000, categories=cats)
        mock_cache.get_month = AsyncMock(return_value=month)

        result = json.loads(await get_money_flow(budget_id="bud-1", month="2026-03-01"))
        node_names = [n["name"] for n in result["nodes"]]
        assert "Entertainment" not in node_names

    @pytest.mark.asyncio
    async def test_current_month_resolves(self, mock_cache):
        from src.server import get_money_flow

        month = _make_month_detail(income=0, categories=[])
        mock_cache.get_month = AsyncMock(return_value=month)

        result = json.loads(await get_money_flow(budget_id="bud-1", month="current"))
        # Should have resolved "current" to a YYYY-MM-DD string
        assert result["month"] != "current"
        assert len(result["month"]) == 10  # YYYY-MM-DD


# ── Error Handling ────────────────────────────────────────────


class TestHandleErrors:
    @pytest.mark.asyncio
    async def test_ynab_error(self, mock_cache):
        from src.server import list_budgets
        from src.ynab_client import YNABError

        mock_cache.get_budgets = AsyncMock(side_effect=YNABError(404, "not_found", "Budget not found"))
        result = json.loads(await list_budgets())
        assert result["error"] == "Budget not found"
        assert result["error_id"] == "not_found"
        assert result["status_code"] == 404

    @pytest.mark.asyncio
    async def test_http_status_error(self, mock_cache):
        import httpx
        from src.server import list_budgets

        response = httpx.Response(500, text="Internal Server Error", request=httpx.Request("GET", "https://api.ynab.com"))
        mock_cache.get_budgets = AsyncMock(side_effect=httpx.HTTPStatusError("error", request=response.request, response=response))
        result = json.loads(await list_budgets())
        assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    async def test_request_error(self, mock_cache):
        import httpx
        from src.server import list_budgets

        mock_cache.get_budgets = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        result = json.loads(await list_budgets())
        assert "Request failed" in result["error"]

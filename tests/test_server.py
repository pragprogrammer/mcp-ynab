"""Tests for MCP server tools.

Tests each tool by mocking the CacheService so no real YNAB API calls are made.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.models import (
    Account,
    PlanDetail,
    PlanSummary,
    Category,
    CategoryGroup,
    MonthDetail,
    MonthSummary,
    Payee,
    ScheduledTransaction,
    Transaction,
    User,
)


# ── Fixtures ──────────────────────────────────────────────────


def _make_transaction(**overrides) -> Transaction:
    defaults = {"id": "txn-1", "date": "2026-03-15", "amount": -50250}
    return Transaction(**{**defaults, **overrides})


def _make_account(**overrides) -> Account:
    defaults = {"id": "acc-1", "name": "Checking", "type": "checking"}
    return Account(**{**defaults, **overrides})


def _make_plan_summary(**overrides) -> PlanSummary:
    defaults = {"id": "bud-1", "name": "My Plan", "last_modified_on": "2026-03-15"}
    return PlanSummary(**{**defaults, **overrides})


def _make_plan_detail(**overrides) -> PlanDetail:
    defaults = {"id": "bud-1", "name": "My Plan", "last_modified_on": "2026-03-15"}
    return PlanDetail(**{**defaults, **overrides})


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


# We need to patch the module-level objects in server/_shared.py.
# The server package creates `cache` and `client` at import time,
# so we patch `src.server._shared.cache` (the CacheService instance).

CACHE_PATH = "src.server._shared.cache"
DB_PATH = "src.server._shared._ensure_db"


@pytest.fixture
def mock_cache():
    with patch(CACHE_PATH) as mock, patch(DB_PATH, new_callable=AsyncMock):
        yield mock


# ── Plan Tools ──────────────────────────────────────────────


class TestListPlans:
    @pytest.mark.asyncio
    async def test_returns_plans(self, mock_cache):
        from src.server import list_plans

        mock_cache.get_plans = AsyncMock(return_value=[_make_plan_summary()])
        result = json.loads(await list_plans())
        assert len(result) == 1
        assert result[0]["id"] == "bud-1"
        assert result[0]["name"] == "My Plan"

    @pytest.mark.asyncio
    async def test_empty_plans(self, mock_cache):
        from src.server import list_plans

        mock_cache.get_plans = AsyncMock(return_value=[])
        result = json.loads(await list_plans())
        assert result == []


class TestGetPlan:
    @pytest.mark.asyncio
    async def test_returns_plan_detail(self, mock_cache):
        from src.server import get_plan

        mock_cache.get_plan = AsyncMock(return_value=_make_plan_detail())
        result = json.loads(await get_plan(plan_id="bud-1"))
        assert result["id"] == "bud-1"
        # last_modified_on is excluded by default; pass exclude_fields=[] to include it
        assert "last_modified_on" not in result

    @pytest.mark.asyncio
    async def test_exclude_fields_empty_returns_all(self, mock_cache):
        from src.server import get_plan

        mock_cache.get_plan = AsyncMock(return_value=_make_plan_detail())
        result = json.loads(await get_plan(plan_id="bud-1", exclude_fields=[]))
        assert result["last_modified_on"] == "2026-03-15"

    @pytest.mark.asyncio
    async def test_exclude_fields_custom_overrides_default(self, mock_cache):
        from src.server import get_plan

        mock_cache.get_plan = AsyncMock(return_value=_make_plan_detail())
        # Pass a custom list — defaults are ignored, only `name` excluded
        result = json.loads(await get_plan(plan_id="bud-1", exclude_fields=["name"]))
        assert result["last_modified_on"] == "2026-03-15"
        assert "name" not in result


# ── Account Tools ─────────────────────────────────────────────


class TestListAccounts:
    @pytest.mark.asyncio
    async def test_returns_accounts(self, mock_cache):
        from src.server import list_accounts

        mock_cache.get_accounts = AsyncMock(return_value=[_make_account()])
        result = json.loads(await list_accounts(plan_id="bud-1"))
        assert len(result) == 1
        assert result[0]["name"] == "Checking"
        # `deleted` is excluded by default; pass exclude_fields=[] to include it
        assert "deleted" not in result[0]


class TestGetAccount:
    @pytest.mark.asyncio
    async def test_returns_single_account(self, mock_cache):
        from src.server import get_account

        mock_cache.get_account = AsyncMock(return_value=_make_account())
        result = json.loads(await get_account(account_id="acc-1", plan_id="bud-1"))
        assert result["id"] == "acc-1"


# ── Transaction Tools ─────────────────────────────────────────


class TestListTransactions:
    @pytest.mark.asyncio
    async def test_returns_transactions(self, mock_cache):
        from src.server import list_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await list_transactions(plan_id="bud-1"))
        assert len(result) == 1
        assert result[0]["amount"] == -50.25

    @pytest.mark.asyncio
    async def test_passes_filters(self, mock_cache):
        from src.server import list_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[])
        await list_transactions(plan_id="bud-1", since_date="2026-01-01", type="uncategorized")
        mock_cache.get_transactions.assert_called_once_with("bud-1", "2026-01-01", "uncategorized")


class TestGetTransaction:
    @pytest.mark.asyncio
    async def test_returns_single_transaction(self, mock_cache):
        from src.server import get_transaction

        mock_cache.get_transaction = AsyncMock(return_value=_make_transaction())
        result = json.loads(await get_transaction(transaction_id="txn-1", plan_id="bud-1"))
        assert result["id"] == "txn-1"


class TestGetTransactionsByAccount:
    @pytest.mark.asyncio
    async def test_returns_filtered_transactions(self, mock_cache):
        from src.server import get_transactions_by_account

        mock_cache.get_transactions_by_account = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await get_transactions_by_account(account_id="acc-1", plan_id="bud-1"))
        assert len(result) == 1


class TestGetTransactionsByCategory:
    @pytest.mark.asyncio
    async def test_returns_filtered_transactions(self, mock_cache):
        from src.server import get_transactions_by_category

        mock_cache.get_transactions_by_category = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await get_transactions_by_category(category_id="cat-1", plan_id="bud-1"))
        assert len(result) == 1


class TestGetTransactionsByPayee:
    @pytest.mark.asyncio
    async def test_returns_filtered_transactions(self, mock_cache):
        from src.server import get_transactions_by_payee

        mock_cache.get_transactions_by_payee = AsyncMock(return_value=[_make_transaction()])
        result = json.loads(await get_transactions_by_payee(payee_id="pay-1", plan_id="bud-1"))
        assert len(result) == 1


class TestCreateTransaction:
    @pytest.mark.asyncio
    async def test_converts_dollars_to_milliunits(self, mock_cache):
        from src.server import create_transaction

        mock_cache.create_transaction = AsyncMock(return_value=_make_transaction(amount=-50250))
        await create_transaction(
            plan_id="bud-1", account_id="acc-1", date="2026-03-15", amount=-50.25,
        )
        call_args = mock_cache.create_transaction.call_args
        txn_dict = call_args[0][0]
        assert txn_dict["amount"] == -50250

    @pytest.mark.asyncio
    async def test_includes_optional_fields(self, mock_cache):
        from src.server import create_transaction

        mock_cache.create_transaction = AsyncMock(return_value=_make_transaction())
        await create_transaction(
            plan_id="bud-1", account_id="acc-1", date="2026-03-15", amount=-10.0,
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
            plan_id="bud-1", account_id="acc-1", date="2026-03-15", amount=-10.0,
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
            plan_id="bud-1",
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
            plan_id="bud-1",
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
            plan_id="bud-1",
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
        await update_transaction(plan_id="bud-1", transaction_id="txn-1", amount=-75.00)
        call_args = mock_cache.update_transaction.call_args
        txn_dict = call_args[0][1]
        assert txn_dict["amount"] == -75000

    @pytest.mark.asyncio
    async def test_only_includes_provided_fields(self, mock_cache):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock(return_value=_make_transaction())
        await update_transaction(plan_id="bud-1", transaction_id="txn-1", memo="updated")
        txn_dict = mock_cache.update_transaction.call_args[0][1]
        assert txn_dict == {"memo": "updated"}


class TestDeleteTransaction:
    @pytest.mark.asyncio
    async def test_deletes_and_returns(self, mock_cache):
        from src.server import delete_transaction

        mock_cache.delete_transaction = AsyncMock(return_value=_make_transaction())
        result = json.loads(await delete_transaction(transaction_id="txn-1", plan_id="bud-1"))
        assert result["id"] == "txn-1"


class TestUpdateTransactions:
    @pytest.mark.asyncio
    async def test_converts_amounts_to_milliunits(self, mock_cache):
        from src.server import update_transactions

        mock_cache.update_transactions = AsyncMock(
            return_value=[_make_transaction(id="t1"), _make_transaction(id="t2")]
        )
        await update_transactions(
            plan_id="bud-1",
            transactions=[
                {"id": "t1", "amount": -25.50},
                {"id": "t2", "amount": 10.00},
            ],
        )
        prepared = mock_cache.update_transactions.call_args[0][0]
        assert prepared[0]["amount"] == -25500
        assert prepared[1]["amount"] == 10000

    @pytest.mark.asyncio
    async def test_only_includes_provided_fields(self, mock_cache):
        from src.server import update_transactions

        mock_cache.update_transactions = AsyncMock(
            return_value=[_make_transaction(id="t1")]
        )
        await update_transactions(
            plan_id="bud-1",
            transactions=[{"id": "t1", "memo": "updated"}],
        )
        prepared = mock_cache.update_transactions.call_args[0][0]
        assert prepared[0] == {"id": "t1", "memo": "updated"}

    @pytest.mark.asyncio
    async def test_requires_id_per_transaction(self, mock_cache):
        from src.server import update_transactions

        result = json.loads(await update_transactions(
            plan_id="bud-1",
            transactions=[{"memo": "no id here"}],
        ))
        assert "error" in result
        assert "id" in result["error"]


# ── Category Tools ────────────────────────────────────────────


class TestListCategories:
    @pytest.mark.asyncio
    async def test_returns_grouped_categories(self, mock_cache):
        from src.server import list_categories

        cat = _make_category()
        group = _make_category_group(categories=[cat])
        mock_cache.get_categories = AsyncMock(return_value=[group])
        result = json.loads(await list_categories(plan_id="bud-1"))
        assert len(result) == 1
        assert result[0]["name"] == "Bills"
        assert len(result[0]["categories"]) == 1

    @pytest.mark.asyncio
    async def test_nested_categories_apply_default_excludes(self, mock_cache):
        from src.server import list_categories

        cat = _make_category(
            original_category_group_id="orig-grp",
            goal_target_month="2026-01-01",
        )
        group = _make_category_group(categories=[cat], deleted=True)
        mock_cache.get_categories = AsyncMock(return_value=[group])
        result = json.loads(await list_categories(plan_id="bud-1"))

        assert "deleted" not in result[0]
        nested = result[0]["categories"][0]
        assert "original_category_group_id" not in nested
        assert "goal_target_month" not in nested
        assert nested["name"] == "Food"

    @pytest.mark.asyncio
    async def test_nested_excludes_apply_even_with_top_level_override(self, mock_cache):
        from src.server import list_categories

        cat = _make_category(original_category_group_id="orig-grp")
        group = _make_category_group(categories=[cat], deleted=True)
        mock_cache.get_categories = AsyncMock(return_value=[group])
        result = json.loads(await list_categories(plan_id="bud-1", exclude_fields=[]))

        assert result[0]["deleted"] is True  # caller asked for everything top-level
        assert "original_category_group_id" not in result[0]["categories"][0]


class TestGetCategoryForMonth:
    @pytest.mark.asyncio
    async def test_returns_category_with_goals(self, mock_cache):
        from src.server import get_category_for_month

        cat = _make_category(goal_type="TB", goal_target=500000, budgeted=250000)
        mock_cache.get_category_for_month = AsyncMock(return_value=cat)
        result = json.loads(await get_category_for_month(
            category_id="cat-1", month="2026-03-01", plan_id="bud-1"
        ))
        assert result["goal_type"] == "TB"


class TestUpdateCategoryForMonth:
    @pytest.mark.asyncio
    async def test_converts_dollars_to_milliunits(self, mock_cache):
        from src.server import update_category_for_month

        mock_cache.update_category_for_month = AsyncMock(return_value=_make_category(budgeted=500000))
        await update_category_for_month(
            category_id="cat-1", month="2026-03-01", budgeted=500.00, plan_id="bud-1"
        )
        call_args = mock_cache.update_category_for_month.call_args
        assert call_args[0][2] == 500000  # third positional arg is budgeted in milliunits


# ── Payee Tools ───────────────────────────────────────────────


class TestListPayees:
    @pytest.mark.asyncio
    async def test_returns_payees(self, mock_cache):
        from src.server import list_payees

        mock_cache.get_payees = AsyncMock(return_value=[_make_payee()])
        result = json.loads(await list_payees(plan_id="bud-1"))
        assert len(result) == 1
        assert result[0]["name"] == "Amazon"


# ── Month Tools ───────────────────────────────────────────────


class TestListMonths:
    @pytest.mark.asyncio
    async def test_returns_months(self, mock_cache):
        from src.server import list_months

        mock_cache.get_months = AsyncMock(return_value=[_make_month_summary()])
        result = json.loads(await list_months(plan_id="bud-1"))
        assert len(result) == 1
        assert result[0]["income"] == 5000.0


class TestGetMonth:
    @pytest.mark.asyncio
    async def test_returns_month_with_categories(self, mock_cache):
        from src.server import get_month

        mock_cache.get_month = AsyncMock(return_value=_make_month_detail())
        result = json.loads(await get_month(month="2026-03-01", plan_id="bud-1"))
        assert "categories" in result
        assert result["income"] == 5000.0

    @pytest.mark.asyncio
    async def test_nested_categories_apply_default_excludes(self, mock_cache):
        from src.server import get_month

        cat = _make_category(
            original_category_group_id="orig-grp",
            goal_cadence=1,
        )
        mock_cache.get_month = AsyncMock(return_value=_make_month_detail(categories=[cat]))
        result = json.loads(await get_month(month="2026-03-01", plan_id="bud-1"))

        nested = result["categories"][0]
        assert "original_category_group_id" not in nested
        assert "goal_cadence" not in nested
        assert nested["name"] == "Food"


# ── Scheduled Transactions ────────────────────────────────────


class TestListScheduledTransactions:
    @pytest.mark.asyncio
    async def test_returns_scheduled(self, mock_cache):
        from src.server import list_scheduled_transactions

        mock_cache.get_scheduled_transactions = AsyncMock(
            return_value=[_make_scheduled_transaction()]
        )
        result = json.loads(await list_scheduled_transactions(plan_id="bud-1"))
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

        result = json.loads(await get_money_flow(plan_id="bud-1", month="2026-03-01"))
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

        result = json.loads(await get_money_flow(plan_id="bud-1", month="2026-03-01"))
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

        result = json.loads(await get_money_flow(plan_id="bud-1", month="2026-03-01"))
        node_names = [n["name"] for n in result["nodes"]]
        assert "Entertainment" not in node_names

    @pytest.mark.asyncio
    async def test_current_month_resolves(self, mock_cache):
        from src.server import get_money_flow

        month = _make_month_detail(income=0, categories=[])
        mock_cache.get_month = AsyncMock(return_value=month)

        result = json.loads(await get_money_flow(plan_id="bud-1", month="current"))
        # Should have resolved "current" to a YYYY-MM-DD string
        assert result["month"] != "current"
        assert len(result["month"]) == 10  # YYYY-MM-DD


# ── Search Transactions ──────────────────────────────────────


class TestSearchTransactions:
    @pytest.mark.asyncio
    async def test_matches_payee_name(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(payee_name="Whole Foods", memo=None, category_name="Groceries"),
            _make_transaction(id="txn-2", payee_name="Target", memo=None, category_name="Shopping"),
        ])
        result = json.loads(await search_transactions(plan_id="bud-1", query="whole"))
        assert len(result) == 1
        assert result[0]["payee_name"] == "Whole Foods"

    @pytest.mark.asyncio
    async def test_matches_memo(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(payee_name="Store", memo="birthday gift", category_name=None),
        ])
        result = json.loads(await search_transactions(plan_id="bud-1", query="birthday"))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_matches_category_name(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(payee_name="Shell", memo=None, category_name="Gas & Fuel"),
        ])
        result = json.loads(await search_transactions(plan_id="bud-1", query="fuel"))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_amount_range_filter(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(id="t1", payee_name="A", amount=-10000),   # -$10
            _make_transaction(id="t2", payee_name="A", amount=-50000),   # -$50
            _make_transaction(id="t3", payee_name="A", amount=-100000),  # -$100
        ])
        result = json.loads(await search_transactions(
            plan_id="bud-1", query="A", amount_min=-60.0, amount_max=-5.0
        ))
        assert len(result) == 2
        amounts = {r["amount"] for r in result}
        assert amounts == {-10.0, -50.0}

    @pytest.mark.asyncio
    async def test_combined_filters(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(id="t1", payee_name="Cafe", amount=-5000),
            _make_transaction(id="t2", payee_name="Cafe", amount=-25000),
            _make_transaction(id="t3", payee_name="Store", amount=-5000),
        ])
        result = json.loads(await search_transactions(
            plan_id="bud-1", query="cafe", amount_min=-10.0
        ))
        assert len(result) == 1
        assert result[0]["amount"] == -5.0

    @pytest.mark.asyncio
    async def test_no_results(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(payee_name="Store", memo=None, category_name="Shopping"),
        ])
        result = json.loads(await search_transactions(plan_id="bud-1", query="nonexistent"))
        assert result == []

    @pytest.mark.asyncio
    async def test_amount_range_abs_value_when_both_positive(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(id="t1", payee_name="A", amount=-50000),   # outflow $50
            _make_transaction(id="t2", payee_name="A", amount=-200000),  # outflow $200
            _make_transaction(id="t3", payee_name="A", amount=200000),   # inflow $200
        ])
        result = json.loads(await search_transactions(
            plan_id="bud-1", query="A", amount_min=10.0, amount_max=100.0
        ))
        assert len(result) == 1
        assert result[0]["amount"] == -50.0

    @pytest.mark.asyncio
    async def test_amount_range_signed_when_negative_bound(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(id="t1", payee_name="A", amount=-50000),   # outflow $50
            _make_transaction(id="t2", payee_name="A", amount=50000),    # inflow $50
        ])
        result = json.loads(await search_transactions(
            plan_id="bud-1", query="A", amount_min=-100.0, amount_max=-10.0
        ))
        assert len(result) == 1
        assert result[0]["amount"] == -50.0

    @pytest.mark.asyncio
    async def test_amount_range_positive_bounds_skip_outflows_outside_abs_range(self, mock_cache):
        from src.server import search_transactions

        mock_cache.get_transactions = AsyncMock(return_value=[
            _make_transaction(id="t1", payee_name="A", amount=2000000),  # inflow $2000
        ])
        result = json.loads(await search_transactions(
            plan_id="bud-1", query="A", amount_min=10.0, amount_max=100.0
        ))
        assert result == []


# ── Spending By Category ─────────────────────────────────────


class TestGetSpendingByCategory:
    @pytest.mark.asyncio
    async def test_basic_breakdown(self, mock_cache):
        from src.server import get_spending_by_category

        cats = [
            _make_category(name="Rent", category_group_name="Housing", activity=-1500000, budgeted=1500000, balance=0),
            _make_category(name="Food", category_group_name="Groceries", activity=-500000, budgeted=600000, balance=100000),
        ]
        mock_cache.get_month = AsyncMock(return_value=_make_month_detail(categories=cats))
        result = json.loads(await get_spending_by_category(plan_id="bud-1", month="2026-03-01"))
        assert result["total_spent"] == 2000.0
        assert len(result["categories"]) == 2
        # Sorted by spending highest first
        assert result["categories"][0]["name"] == "Rent"
        assert result["categories"][0]["spent"] == 1500.0
        assert result["categories"][0]["pct_of_total"] == 75.0

    @pytest.mark.asyncio
    async def test_excludes_zero_activity(self, mock_cache):
        from src.server import get_spending_by_category

        cats = [
            _make_category(name="Rent", category_group_name="Housing", activity=-1000000, budgeted=1000000),
            _make_category(name="Unused", category_group_name="Entertainment", activity=0, budgeted=200000),
        ]
        mock_cache.get_month = AsyncMock(return_value=_make_month_detail(categories=cats))
        result = json.loads(await get_spending_by_category(plan_id="bud-1", month="2026-03-01"))
        names = [c["name"] for c in result["categories"]]
        assert "Unused" not in names

    @pytest.mark.asyncio
    async def test_excludes_internal_groups(self, mock_cache):
        from src.server import get_spending_by_category

        cats = [
            _make_category(name="Rent", category_group_name="Housing", activity=-1000000),
            _make_category(name="Transfer", category_group_name="Internal Master Category", activity=-500000),
            _make_category(name="CC", category_group_name="Credit Card Payments", activity=-200000),
        ]
        mock_cache.get_month = AsyncMock(return_value=_make_month_detail(categories=cats))
        result = json.loads(await get_spending_by_category(plan_id="bud-1", month="2026-03-01"))
        groups = {c["group"] for c in result["categories"]}
        assert "Internal Master Category" not in groups
        assert "Credit Card Payments" not in groups

    @pytest.mark.asyncio
    async def test_current_month_default(self, mock_cache):
        from src.server import get_spending_by_category

        mock_cache.get_month = AsyncMock(return_value=_make_month_detail(categories=[]))
        result = json.loads(await get_spending_by_category(plan_id="bud-1"))
        assert result["month"] != "current"
        assert len(result["month"]) == 10


# ── Error Handling ────────────────────────────────────────────


class TestHandleErrors:
    @pytest.mark.asyncio
    async def test_ynab_error(self, mock_cache):
        from src.server import list_plans
        from src.ynab_client import YNABError

        mock_cache.get_plans = AsyncMock(side_effect=YNABError(404, "not_found", "Plan not found"))
        result = json.loads(await list_plans())
        assert result["error"] == "Plan not found"
        assert result["error_id"] == "not_found"
        assert result["status_code"] == 404

    @pytest.mark.asyncio
    async def test_http_status_error(self, mock_cache):
        import httpx
        from src.server import list_plans

        response = httpx.Response(500, text="Internal Server Error", request=httpx.Request("GET", "https://api.ynab.com"))
        mock_cache.get_plans = AsyncMock(side_effect=httpx.HTTPStatusError("error", request=response.request, response=response))
        result = json.loads(await list_plans())
        assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    async def test_request_error(self, mock_cache):
        import httpx
        from src.server import list_plans

        mock_cache.get_plans = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        result = json.loads(await list_plans())
        assert "Request failed" in result["error"]


# ── User Tools ───────────────────────────────────────────────


class TestGetUser:
    @pytest.mark.asyncio
    async def test_returns_user(self, mock_cache):
        from src.server import get_user

        mock_cache.get_user = AsyncMock(return_value=User(id="user-123"))
        result = json.loads(await get_user())
        assert result["id"] == "user-123"

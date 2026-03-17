"""Tests for YNABClient API client.

Tests each method by mocking httpx responses.
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.ynab_client import YNABClient, YNABError


@pytest.fixture
def client():
    return YNABClient(api_key="test-key", timeout=5.0)


def _mock_response(data: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "https://api.ynab.com/v1/test"),
    )


def _error_response(status_code: int, error_id: str, detail: str) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json={"error": {"id": error_id, "detail": detail}},
        request=httpx.Request("GET", "https://api.ynab.com/v1/test"),
    )


# ── Error Handling ────────────────────────────────────────────


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_ynab_error_raised(self, client):
        response = _error_response(404, "not_found", "Budget not found")
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=response)

        with pytest.raises(YNABError) as exc_info:
            await client.get_budgets()

        assert exc_info.value.status_code == 404
        assert exc_info.value.error_id == "not_found"
        assert exc_info.value.message == "Budget not found"

    @pytest.mark.asyncio
    async def test_authorization_header(self, client):
        assert client._client.headers["Authorization"] == "Bearer test-key"


# ── Budgets ───────────────────────────────────────────────────


class TestGetBudgets:
    @pytest.mark.asyncio
    async def test_returns_budget_summaries(self, client):
        data = {"data": {"budgets": [
            {"id": "b1", "name": "My Budget", "last_modified_on": "2026-03-15"},
        ]}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        result = await client.get_budgets()
        assert len(result) == 1
        assert result[0].id == "b1"
        assert result[0].name == "My Budget"


class TestGetBudget:
    @pytest.mark.asyncio
    async def test_returns_budget_detail(self, client):
        data = {"data": {"budget": {
            "id": "b1", "name": "My Budget", "last_modified_on": "2026-03-15",
        }}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        result = await client.get_budget("b1")
        assert result.id == "b1"


# ── Accounts ──────────────────────────────────────────────────


class TestGetAccounts:
    @pytest.mark.asyncio
    async def test_returns_accounts_and_knowledge(self, client):
        data = {"data": {
            "accounts": [{"id": "a1", "name": "Checking", "type": "checking"}],
            "server_knowledge": 42,
        }}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        accounts, knowledge = await client.get_accounts("b1")
        assert len(accounts) == 1
        assert accounts[0].name == "Checking"
        assert knowledge == 42

    @pytest.mark.asyncio
    async def test_passes_server_knowledge(self, client):
        data = {"data": {"accounts": [], "server_knowledge": 50}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        await client.get_accounts("b1", last_knowledge_of_server=42)
        call_args = client._client.get.call_args
        assert call_args[1]["params"]["last_knowledge_of_server"] == 42


# ── Transactions ──────────────────────────────────────────────


class TestGetTransactions:
    @pytest.mark.asyncio
    async def test_returns_transactions_and_knowledge(self, client):
        data = {"data": {
            "transactions": [{"id": "t1", "date": "2026-03-15", "amount": -50250}],
            "server_knowledge": 10,
        }}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        txns, knowledge = await client.get_transactions("b1")
        assert len(txns) == 1
        assert txns[0].amount == -50250
        assert knowledge == 10

    @pytest.mark.asyncio
    async def test_passes_filters(self, client):
        data = {"data": {"transactions": [], "server_knowledge": 0}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        await client.get_transactions("b1", since_date="2026-01-01", type="uncategorized")
        params = client._client.get.call_args[1]["params"]
        assert params["since_date"] == "2026-01-01"
        assert params["type"] == "uncategorized"


class TestCreateTransaction:
    @pytest.mark.asyncio
    async def test_creates_transaction(self, client):
        data = {"data": {"transaction": {
            "id": "t1", "date": "2026-03-15", "amount": -50250,
        }}}
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=_mock_response(data))

        txn_data = {"account_id": "a1", "date": "2026-03-15", "amount": -50250}
        result = await client.create_transaction(txn_data, "b1")
        assert result.id == "t1"
        assert result.amount == -50250

        # Verify the post payload
        post_call = client._client.post.call_args
        assert post_call[1]["json"] == {"transaction": txn_data}


class TestCreateTransactions:
    @pytest.mark.asyncio
    async def test_creates_bulk_transactions(self, client):
        data = {"data": {"transactions": [
            {"id": "t1", "date": "2026-03-15", "amount": -10000},
            {"id": "t2", "date": "2026-03-16", "amount": -20000},
        ]}}
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=_mock_response(data))

        txns_data = [
            {"account_id": "a1", "date": "2026-03-15", "amount": -10000},
            {"account_id": "a1", "date": "2026-03-16", "amount": -20000},
        ]
        result = await client.create_transactions(txns_data, "b1")
        assert len(result) == 2
        assert result[0].id == "t1"
        assert result[1].id == "t2"

        post_call = client._client.post.call_args
        assert post_call[1]["json"] == {"transactions": txns_data}


class TestUpdateTransaction:
    @pytest.mark.asyncio
    async def test_updates_transaction(self, client):
        data = {"data": {"transaction": {
            "id": "t1", "date": "2026-03-15", "amount": -75000, "memo": "updated",
        }}}
        client._client = AsyncMock()
        client._client.put = AsyncMock(return_value=_mock_response(data))

        result = await client.update_transaction("t1", {"memo": "updated"}, "b1")
        assert result.memo == "updated"


class TestDeleteTransaction:
    @pytest.mark.asyncio
    async def test_deletes_transaction(self, client):
        data = {"data": {"transaction": {
            "id": "t1", "date": "2026-03-15", "amount": -50250, "deleted": True,
        }}}
        client._client = AsyncMock()
        client._client.delete = AsyncMock(return_value=_mock_response(data))

        result = await client.delete_transaction("t1", "b1")
        assert result.id == "t1"


# ── Categories ────────────────────────────────────────────────


class TestGetCategories:
    @pytest.mark.asyncio
    async def test_returns_category_groups(self, client):
        data = {"data": {
            "category_groups": [{
                "id": "g1", "name": "Bills", "hidden": False, "deleted": False,
                "categories": [{"id": "c1", "category_group_id": "g1", "name": "Rent"}],
            }],
            "server_knowledge": 5,
        }}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        groups, knowledge = await client.get_categories("b1")
        assert len(groups) == 1
        assert groups[0].name == "Bills"
        assert len(groups[0].categories) == 1
        assert knowledge == 5


class TestUpdateCategoryBudget:
    @pytest.mark.asyncio
    async def test_updates_budget(self, client):
        data = {"data": {"category": {
            "id": "c1", "category_group_id": "g1", "name": "Rent", "budgeted": 500000,
        }}}
        client._client = AsyncMock()
        client._client.patch = AsyncMock(return_value=_mock_response(data))

        result = await client.update_category_budget("2026-03-01", "c1", 500000, "b1")
        assert result.budgeted == 500000

        patch_call = client._client.patch.call_args
        assert patch_call[1]["json"] == {"category": {"budgeted": 500000}}


# ── Payees ────────────────────────────────────────────────────


class TestGetPayees:
    @pytest.mark.asyncio
    async def test_returns_payees(self, client):
        data = {"data": {
            "payees": [{"id": "p1", "name": "Amazon"}],
            "server_knowledge": 3,
        }}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        payees, knowledge = await client.get_payees("b1")
        assert len(payees) == 1
        assert payees[0].name == "Amazon"


# ── Months ────────────────────────────────────────────────────


class TestGetMonths:
    @pytest.mark.asyncio
    async def test_returns_month_summaries(self, client):
        data = {"data": {
            "months": [{"month": "2026-03-01", "income": 5000000}],
            "server_knowledge": 7,
        }}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        months, knowledge = await client.get_months("b1")
        assert len(months) == 1
        assert months[0].income == 5000000


class TestGetMonth:
    @pytest.mark.asyncio
    async def test_returns_month_detail(self, client):
        data = {"data": {"month": {
            "month": "2026-03-01", "income": 5000000,
            "categories": [{"id": "c1", "category_group_id": "g1", "name": "Food"}],
        }}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        result = await client.get_month("2026-03-01", "b1")
        assert result.income == 5000000
        assert len(result.categories) == 1


# ── Scheduled Transactions ───────────────────────────────────


class TestGetScheduledTransactions:
    @pytest.mark.asyncio
    async def test_returns_scheduled(self, client):
        data = {"data": {"scheduled_transactions": [
            {"id": "st1", "date_next": "2026-04-01", "frequency": "monthly", "amount": -10000},
        ]}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        result = await client.get_scheduled_transactions("b1")
        assert len(result) == 1
        assert result[0].frequency == "monthly"


# ── URL Construction ──────────────────────────────────────────


class TestURLConstruction:
    @pytest.mark.asyncio
    async def test_budget_url(self, client):
        data = {"data": {"budget": {"id": "b1", "name": "Test", "last_modified_on": "2026-01-01"}}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        await client.get_budget("b1")
        url = client._client.get.call_args[0][0]
        assert url == "/budgets/b1"

    @pytest.mark.asyncio
    async def test_transaction_by_category_url(self, client):
        data = {"data": {"transactions": [], "server_knowledge": 0}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        await client.get_transactions_by_category("c1", "b1")
        url = client._client.get.call_args[0][0]
        assert url == "/budgets/b1/categories/c1/transactions"

    @pytest.mark.asyncio
    async def test_month_category_url(self, client):
        data = {"data": {"category": {"id": "c1", "category_group_id": "g1", "name": "Food"}}}
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=_mock_response(data))

        await client.get_category_for_month("2026-03-01", "c1", "b1")
        url = client._client.get.call_args[0][0]
        assert url == "/budgets/b1/months/2026-03-01/categories/c1"

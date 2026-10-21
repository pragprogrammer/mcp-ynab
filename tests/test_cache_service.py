"""Tests for CacheService transaction history handling.

YNAB returns only roughly the last year of transactions when no since_date is
sent, so the cache must always request full history explicitly.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

import src.db.engine as db_engine
from src.cache.service import (
    ENDPOINT_TRANSACTIONS,
    FULL_HISTORY_SINCE,
    CacheService,
)
from src.db.engine import get_session, init_db
from src.db.tables import ServerKnowledge
from src.models import Transaction


def _settings():
    s = MagicMock()
    s.delta_min_interval = 0
    s.retry_max_attempts = 1
    s.retry_base_delay = 0
    s.retry_max_delay = 0
    s.ttl_single_entity = 60
    return s


def _txn(id: str, date: str) -> Transaction:
    return Transaction(id=id, date=date, amount=-1000)


@pytest_asyncio.fixture
async def db(tmp_path):
    db_engine._engine = None
    db_engine._session_factory = None
    await init_db(str(tmp_path / "cache.db"))
    yield
    await db_engine._engine.dispose()
    db_engine._engine = None
    db_engine._session_factory = None


@pytest.fixture
def client():
    c = MagicMock()
    c.get_transactions = AsyncMock(
        return_value=([_txn("old", "2023-05-01"), _txn("new", "2026-10-01")], 42)
    )
    c.get_transactions_by_payee = AsyncMock(return_value=[])
    c.get_transactions_by_category = AsyncMock(return_value=[])
    return c


class TestFullHistorySync:
    @pytest.mark.asyncio
    async def test_initial_sync_requests_full_history(self, db, client):
        cache = CacheService(client, _settings())

        txns = await cache.get_transactions("plan-1")

        client.get_transactions.assert_called_once_with(
            "plan-1", since_date=FULL_HISTORY_SINCE, last_knowledge_of_server=None
        )
        assert {t.id for t in txns} == {"old", "new"}

    @pytest.mark.asyncio
    async def test_old_since_date_returns_old_transactions(self, db, client):
        cache = CacheService(client, _settings())

        txns = await cache.get_transactions("plan-1", since_date="2022-01-01")
        assert {t.id for t in txns} == {"old", "new"}

        txns = await cache.get_transactions("plan-1", since_date="2026-01-01")
        assert {t.id for t in txns} == {"new"}

    @pytest.mark.asyncio
    async def test_delta_sync_keeps_full_history_param(self, db, client):
        cache = CacheService(client, _settings())
        await cache.get_transactions("plan-1")
        client.get_transactions.return_value = ([], 43)

        await cache.get_transactions("plan-1")

        assert client.get_transactions.call_args.kwargs == {
            "since_date": FULL_HISTORY_SINCE,
            "last_knowledge_of_server": 42,
        }

    @pytest.mark.asyncio
    async def test_legacy_one_year_cache_is_rebuilt(self, db, client):
        # A cache written before this fix tracked knowledge under "transactions".
        async with get_session() as session:
            session.add(ServerKnowledge(
                plan_id="plan-1", endpoint="transactions", knowledge=999,
                last_synced_at=datetime.now(timezone.utc),
            ))
            await session.commit()
        assert ENDPOINT_TRANSACTIONS != "transactions"
        cache = CacheService(client, _settings())

        await cache.get_transactions("plan-1")

        # Full fetch, not a delta from the legacy knowledge.
        assert client.get_transactions.call_args.kwargs["last_knowledge_of_server"] is None


class TestDirectTransactionEndpoints:
    @pytest.mark.asyncio
    async def test_by_payee_defaults_to_full_history(self, db, client):
        cache = CacheService(client, _settings())
        await cache.get_transactions_by_payee("payee-1", "plan-1")
        client.get_transactions_by_payee.assert_called_once_with(
            "payee-1", "plan-1", since_date=FULL_HISTORY_SINCE, type=None
        )

    @pytest.mark.asyncio
    async def test_by_payee_respects_caller_since_date(self, db, client):
        cache = CacheService(client, _settings())
        await cache.get_transactions_by_payee("payee-1", "plan-1", since_date="2026-01-01")
        client.get_transactions_by_payee.assert_called_once_with(
            "payee-1", "plan-1", since_date="2026-01-01", type=None
        )

    @pytest.mark.asyncio
    async def test_by_category_defaults_to_full_history(self, db, client):
        cache = CacheService(client, _settings())
        await cache.get_transactions_by_category("cat-1", "plan-1")
        client.get_transactions_by_category.assert_called_once_with(
            "cat-1", "plan-1", since_date=FULL_HISTORY_SINCE, type=None
        )

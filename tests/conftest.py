"""Shared fixtures.

The consent gate means every mutating tool now needs two things the old tests
did not provide: an MCP `Context` it can elicit through, and a `_shared.client`
it can read a pre-image from. Both live here so test_server.py and
test_security.py use the same fakes.
"""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)

from src.models import Account, Category, CategoryGroup, Payee, ScheduledTransaction, Transaction


class FakeSession:
    """Just enough ServerSession to answer the elicitation capability check."""

    def __init__(self, supports_elicitation: bool = True):
        self.supports_elicitation = supports_elicitation

    def check_client_capability(self, capability) -> bool:
        return self.supports_elicitation


class FakeContext:
    """A Context stand-in that records what a human would have been shown.

    `prompts` is the point of this class: tests assert on the text the human
    would actually see, which is the only thing that makes the consent gate
    meaningful.
    """

    def __init__(
        self,
        *,
        action: str = "accept",
        confirm: bool = True,
        supports_elicitation: bool = True,
        raises: Exception | None = None,
    ):
        self.session = FakeSession(supports_elicitation)
        self.prompts: list[str] = []
        self._action = action
        self._confirm = confirm
        self._raises = raises

    @property
    def prompt(self) -> str:
        """The single prompt shown, for the common one-elicitation case."""
        assert len(self.prompts) == 1, f"expected 1 elicitation, saw {len(self.prompts)}"
        return self.prompts[0]

    async def elicit(self, message: str, schema):
        self.prompts.append(message)
        if self._raises is not None:
            raise self._raises
        if self._action == "accept":
            return AcceptedElicitation(data=schema(confirm=self._confirm))
        if self._action == "decline":
            return DeclinedElicitation()
        return CancelledElicitation()


# The server package creates `cache` and `client` at import time, so the tests
# patch the module-level objects in server/_shared.py.
CACHE_PATH = "src.server._shared.cache"
CLIENT_PATH = "src.server._shared.client"
DB_PATH = "src.server._shared._ensure_db"


@pytest.fixture
def mock_cache():
    """Stand in for the CacheService, so no tool reaches a real YNAB API."""
    with patch(CACHE_PATH) as mock, patch(DB_PATH, new_callable=AsyncMock):
        yield mock


@pytest.fixture
def consenting_ctx() -> FakeContext:
    """A client whose human approves the change."""
    return FakeContext()


@pytest.fixture
def declining_ctx() -> FakeContext:
    """A client whose human says no."""
    return FakeContext(action="decline")


@pytest.fixture
def no_elicitation_ctx() -> FakeContext:
    """A client that never advertised elicitation support."""
    return FakeContext(supports_elicitation=False)


@pytest.fixture
def mock_client():
    """Patch the YNAB client used for consent pre-images.

    Pre-images are read through `_shared.client`, never through the cache, so a
    stale cached row cannot produce a false "before". These defaults let a test
    that does not care about the pre-image stay short.
    """
    with patch(CLIENT_PATH) as mock:
        mock.get_transaction = AsyncMock(
            return_value=Transaction(
                id="txn-1", date="2026-03-15", amount=-50250, memo="original",
                payee_name="Original Payee", cleared="uncleared", approved=False,
            )
        )
        mock.get_account = AsyncMock(
            return_value=Account(id="acc-1", name="Checking", type="checking")
        )
        mock.get_accounts = AsyncMock(
            return_value=(
                [Account(id="acc-1", name="Checking", type="checking", direct_import_linked=True)],
                1,
            )
        )
        mock.get_category = AsyncMock(
            return_value=Category(id="cat-1", category_group_id="grp-1", name="Food", budgeted=100000)
        )
        mock.get_category_for_month = AsyncMock(
            return_value=Category(
                id="cat-1", category_group_id="grp-1", name="Food",
                budgeted=100000, activity=-25000, balance=75000,
            )
        )
        mock.get_categories = AsyncMock(
            return_value=([CategoryGroup(id="grp-1", name="Bills")], 1)
        )
        mock.get_payee = AsyncMock(return_value=Payee(id="pay-1", name="Amazon"))
        mock.get_scheduled_transaction = AsyncMock(
            return_value=ScheduledTransaction(
                id="sch-1", date_next="2026-04-01", frequency="monthly",
                amount=-20000, account_id="acc-1", payee_name="Gym",
            )
        )
        yield mock

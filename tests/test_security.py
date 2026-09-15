"""Tests for the security hardening: crypto, credentials, redaction, consent.

The consent tests are the ones that matter. They assert on what a human would
have been shown and on whether a write actually happened — not on the string a
tool returned, which is the easy thing to check and the useless one.
"""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.exceptions import InvalidTag

from src.models import Transaction
from src.security import consent, credentials, crypto, diff, redaction
from src.ynab_client import YNABError


TOKEN = "ynab-pat-0123456789abcdef0123456789abcdef0123456789abcdef"


def _applied() -> Transaction:
    """What the cache service hands back once a write has gone through."""
    return Transaction(id="txn-1", date="2026-03-15", amount=-75000)


# ── Crypto ────────────────────────────────────────────────────


class TestCrypto:
    def test_round_trip(self):
        key = os.urandom(crypto.KEY_BYTES)
        aad = crypto.aad_for("cached_entity", "data")
        envelope = crypto.encrypt(b'{"memo":"lunch"}', aad, key=key)
        assert crypto.decrypt(envelope, aad, key=key) == b'{"memo":"lunch"}'

    def test_plaintext_absent_from_envelope(self):
        key = os.urandom(crypto.KEY_BYTES)
        aad = crypto.aad_for("cached_entity", "data")
        envelope = crypto.encrypt(b"Chez Nowhere", aad, key=key)
        assert b"Chez Nowhere" not in envelope

    def test_nonce_is_fresh_per_encryption(self):
        key = os.urandom(crypto.KEY_BYTES)
        aad = crypto.aad_for("cached_entity", "data")
        first = crypto.encrypt(b"same plaintext", aad, key=key)
        second = crypto.encrypt(b"same plaintext", aad, key=key)
        assert first[: crypto.NONCE_BYTES] != second[: crypto.NONCE_BYTES]
        assert first != second

    def test_tampered_ciphertext_raises(self):
        key = os.urandom(crypto.KEY_BYTES)
        aad = crypto.aad_for("cached_entity", "data")
        envelope = bytearray(crypto.encrypt(b"sensitive", aad, key=key))
        # Flip one bit well past the nonce, inside the ciphertext proper.
        envelope[crypto.NONCE_BYTES + 1] ^= 0x01
        with pytest.raises(InvalidTag):
            crypto.decrypt(bytes(envelope), aad, key=key)

    def test_wrong_aad_fails(self):
        key = os.urandom(crypto.KEY_BYTES)
        envelope = crypto.encrypt(b"sensitive", crypto.aad_for("cached_entity", "data"), key=key)
        with pytest.raises(InvalidTag):
            crypto.decrypt(envelope, crypto.aad_for("response_cache", "data"), key=key)

    def test_wrong_key_fails(self):
        aad = crypto.aad_for("cached_entity", "data")
        envelope = crypto.encrypt(b"sensitive", aad, key=os.urandom(crypto.KEY_BYTES))
        with pytest.raises(InvalidTag):
            crypto.decrypt(envelope, aad, key=os.urandom(crypto.KEY_BYTES))

    def test_short_envelope_rejected(self):
        with pytest.raises(ValueError):
            crypto.decrypt(b"tooshort", crypto.aad_for("t", "c"), key=os.urandom(32))


# ── Credential store ──────────────────────────────────────────


class FakeKeyring:
    """A keyring backend that lives in a dict."""

    def __init__(self):
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, entry):
        return self.store.get((service, entry))

    def set_password(self, service, entry, value):
        self.store[(service, entry)] = value

    def delete_password(self, service, entry):
        del self.store[(service, entry)]


@pytest.fixture
def fake_keyring():
    fake = FakeKeyring()
    with patch.object(credentials, "_keyring", lambda: fake):
        yield fake


class TestCredentialStore:
    def test_store_load_delete(self, fake_keyring):
        assert credentials.load_token() is None
        credentials.store_token(TOKEN)
        assert credentials.load_token() == TOKEN
        assert credentials.delete_token() is True
        assert credentials.load_token() is None

    def test_delete_absent_token_is_not_an_error(self, fake_keyring):
        assert credentials.delete_token() is False

    def test_token_and_cache_key_are_separate_entries(self, fake_keyring):
        credentials.store_token(TOKEN)
        credentials.set_secret(credentials.CACHE_KEY_ENTRY, "a-cache-key")
        assert credentials.load_token() == TOKEN
        assert credentials.get_secret(credentials.CACHE_KEY_ENTRY) == "a-cache-key"
        credentials.delete_token()
        assert credentials.get_secret(credentials.CACHE_KEY_ENTRY) == "a-cache-key"

    def test_fingerprint_never_contains_the_token(self):
        fingerprint = credentials.token_fingerprint(TOKEN)
        assert TOKEN not in fingerprint
        # Nor any run of it long enough to be worth having.
        assert not any(TOKEN[i : i + 12] in fingerprint for i in range(len(TOKEN) - 12))

    def test_fingerprint_of_short_token_is_digest_only(self):
        assert credentials.token_fingerprint("short") == "sha256:f9b0078b5df5"

    def test_fingerprint_of_no_token(self):
        assert credentials.token_fingerprint(None) == "(none)"


# ── Redaction ─────────────────────────────────────────────────


class TestRedaction:
    def setup_method(self):
        redaction.forget_secrets()

    def teardown_method(self):
        redaction.forget_secrets()

    def test_scrub_replaces_registered_secret(self):
        redaction.register_secret(TOKEN)
        assert TOKEN not in redaction.scrub(f"Authorization: Bearer {TOKEN}")
        assert redaction.PLACEHOLDER in redaction.scrub(f"Bearer {TOKEN}")

    def test_scrub_is_a_no_op_without_registration(self):
        assert redaction.scrub("nothing registered") == "nothing registered"

    def test_short_values_are_not_registered(self):
        redaction.register_secret("abc")
        assert redaction.scrub("abc def") == "abc def"

    @pytest.mark.asyncio
    async def test_token_in_exception_does_not_survive_handle_errors(self):
        from src.server import _shared

        redaction.register_secret(TOKEN)

        @_shared.handle_errors
        async def leaky():
            raise YNABError(401, "unauthorized", f"bad header: Bearer {TOKEN}")

        with patch.object(_shared, "_ensure_db", AsyncMock()):
            result = await leaky()

        assert TOKEN not in result
        assert redaction.PLACEHOLDER in json.loads(result)["error"]

    @pytest.mark.asyncio
    async def test_token_in_http_error_body_does_not_survive(self):
        import httpx

        from src.server import _shared

        redaction.register_secret(TOKEN)

        @_shared.handle_errors
        async def leaky():
            response = httpx.Response(500, text=f"upstream echoed Bearer {TOKEN}")
            raise httpx.HTTPStatusError("boom", request=None, response=response)

        with patch.object(_shared, "_ensure_db", AsyncMock()):
            result = await leaky()

        assert TOKEN not in result


# ── Diff rendering ────────────────────────────────────────────


class TestDiffRendering:
    def test_format_money_uses_milliunits(self):
        assert diff.format_money(-50250) == "-$50.25"
        assert diff.format_money(1000) == "$1.00"
        assert diff.format_money(0) == "$0.00"
        assert diff.format_money(None) == "(none)"

    def test_format_money_keeps_sub_cent_precision(self):
        # Rounding this to $50.26 would show a number that is not what is sent.
        assert diff.format_money(50255) == "$50.255"

    def test_diff_only_reports_fields_the_payload_sets(self):
        changes = diff.diff_fields(
            {"amount": -50250, "memo": "old", "approved": False},
            {"amount": -60000},
        )
        assert changes == [("amount", -50250, -60000)]

    def test_diff_reports_a_field_absent_from_the_preimage(self):
        changes = diff.diff_fields({}, {"flag_color": "red"})
        assert len(changes) == 1 and changes[0][0] == "flag_color"

    def test_change_block_renders_money_as_currency(self):
        block = diff.render_change_block([("amount", -50250, -60000)])
        assert "-$50.25" in block and "-$60.00" in block


# ── Consent ───────────────────────────────────────────────────


class TestConsentPrimitives:
    def test_fingerprint_is_order_independent(self):
        assert consent.payload_fingerprint({"a": 1, "b": 2}) == consent.payload_fingerprint(
            {"b": 2, "a": 1}
        )

    def test_fingerprint_changes_with_a_value(self):
        assert consent.payload_fingerprint({"amount": -50250}) != consent.payload_fingerprint(
            {"amount": -50251}
        )

    def test_assert_unchanged_passes_for_the_approved_payload(self):
        payload = {"amount": -50250}
        consent.assert_unchanged(payload, consent.payload_fingerprint(payload))

    def test_assert_unchanged_catches_a_payload_swapped_after_approval(self):
        payload = {"amount": -50250}
        fingerprint = consent.payload_fingerprint(payload)
        payload["amount"] = -99999
        with pytest.raises(consent.ConsentViolation):
            consent.assert_unchanged(payload, fingerprint)


class TestConsentGate:
    """The gate itself, exercised through a real tool."""

    @pytest.mark.asyncio
    async def test_decline_sends_nothing_to_ynab(
        self, mock_cache, mock_client, declining_ctx
    ):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock()
        await update_transaction(
            plan_id="bud-1", transaction_id="txn-1", amount=-75.00, ctx=declining_ctx
        )

        mock_cache.update_transaction.assert_not_called()
        mock_client.update_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_sends_nothing_to_ynab(self, mock_cache, mock_client):
        from tests.conftest import FakeContext

        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock()
        await update_transaction(
            plan_id="bud-1",
            transaction_id="txn-1",
            amount=-75.00,
            ctx=FakeContext(action="cancel"),
        )

        mock_cache.update_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_false_sends_nothing_to_ynab(self, mock_cache, mock_client):
        from tests.conftest import FakeContext

        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock()
        await update_transaction(
            plan_id="bud-1",
            transaction_id="txn-1",
            amount=-75.00,
            ctx=FakeContext(action="accept", confirm=False),
        )

        mock_cache.update_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_client_without_elicitation_sends_nothing_to_ynab(
        self, mock_cache, mock_client, no_elicitation_ctx
    ):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock()
        result = json.loads(
            await update_transaction(
                plan_id="bud-1",
                transaction_id="txn-1",
                amount=-75.00,
                ctx=no_elicitation_ctx,
            )
        )

        mock_cache.update_transaction.assert_not_called()
        assert no_elicitation_ctx.prompts == []
        assert result["applied"] is False
        assert result["reason"] == "consent_unavailable"

    @pytest.mark.asyncio
    async def test_missing_context_sends_nothing_to_ynab(self, mock_cache, mock_client):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock()
        result = json.loads(
            await update_transaction(plan_id="bud-1", transaction_id="txn-1", amount=-75.00)
        )

        mock_cache.update_transaction.assert_not_called()
        assert result["reason"] == "consent_unavailable"

    @pytest.mark.asyncio
    async def test_elicit_raising_sends_nothing_to_ynab(self, mock_cache, mock_client):
        from tests.conftest import FakeContext

        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock()
        result = json.loads(
            await update_transaction(
                plan_id="bud-1",
                transaction_id="txn-1",
                amount=-75.00,
                ctx=FakeContext(raises=RuntimeError("no back-channel")),
            )
        )

        mock_cache.update_transaction.assert_not_called()
        assert result["reason"] == "consent_unavailable"

    @pytest.mark.asyncio
    async def test_applied_payload_matches_the_one_shown(
        self, mock_cache, mock_client, consenting_ctx
    ):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock(return_value=_applied())
        shown = {}
        real_render = consent.render_prompt

        def spy(**kwargs):
            shown["payload"] = kwargs["payload"]
            return real_render(**kwargs)

        with patch.object(consent, "render_prompt", spy):
            await update_transaction(
                plan_id="bud-1",
                transaction_id="txn-1",
                amount=-75.00,
                memo="new memo",
                ctx=consenting_ctx,
            )

        sent = mock_cache.update_transaction.call_args[0][1]
        assert consent.payload_fingerprint(sent) == consent.payload_fingerprint(shown["payload"])
        assert sent == {"amount": -75000, "memo": "new memo"}
        # And the human saw those values, not just a fingerprint of them.
        assert "-$75.00" in consenting_ctx.prompt
        assert "new memo" in consenting_ctx.prompt

    @pytest.mark.asyncio
    async def test_preimage_comes_from_the_api_not_the_cache(
        self, mock_cache, mock_client, consenting_ctx
    ):
        from src.server import update_transaction

        mock_cache.update_transaction = AsyncMock(return_value=_applied())
        mock_cache.get_transaction = AsyncMock()

        await update_transaction(
            plan_id="bud-1", transaction_id="txn-1", amount=-75.00, ctx=consenting_ctx
        )

        # A stale cached row would show the human a false "before".
        mock_client.get_transaction.assert_awaited_once_with("txn-1", "bud-1")
        mock_cache.get_transaction.assert_not_called()
        assert "Original Payee" in consenting_ctx.prompt
        assert "-$50.25" in consenting_ctx.prompt

    @pytest.mark.asyncio
    async def test_bulk_update_itemises_every_row(
        self, mock_cache, mock_client, consenting_ctx
    ):
        from src.server import update_transactions

        rows = 12
        mock_cache.update_transactions = AsyncMock(return_value=[])
        await update_transactions(
            plan_id="bud-1",
            transactions=[{"id": f"t{i}", "memo": f"memo {i}"} for i in range(rows)],
            ctx=consenting_ctx,
        )

        prompt = consenting_ctx.prompt
        # Never summarised as "12 transactions": every row is spelled out.
        for i in range(rows):
            assert f"memo {i}" in prompt, f"row {i} was not shown to the human"
        assert mock_client.get_transaction.await_count == rows

    @pytest.mark.asyncio
    async def test_bulk_create_itemises_every_row(
        self, mock_cache, mock_client, consenting_ctx
    ):
        from src.server import create_transactions

        mock_cache.create_transactions = AsyncMock(return_value=[])
        await create_transactions(
            plan_id="bud-1",
            account_id="acc-1",
            transactions=[
                {"date": "2026-03-15", "amount": -25.50, "payee_name": "Alpha"},
                {"date": "2026-03-16", "amount": -10.00, "payee_name": "Beta"},
                {"date": "2026-03-17", "amount": -1.25, "payee_name": "Gamma"},
            ],
            ctx=consenting_ctx,
        )

        prompt = consenting_ctx.prompt
        for payee, amount in (("Alpha", "-$25.50"), ("Beta", "-$10.00"), ("Gamma", "-$1.25")):
            assert payee in prompt and amount in prompt

    @pytest.mark.asyncio
    async def test_delete_shows_what_is_being_destroyed(
        self, mock_cache, mock_client, consenting_ctx
    ):
        from src.server import delete_transaction

        mock_cache.delete_transaction = AsyncMock(return_value=_applied())
        await delete_transaction(
            transaction_id="txn-1", plan_id="bud-1", ctx=consenting_ctx
        )

        assert "Original Payee" in consenting_ctx.prompt
        assert "-$50.25" in consenting_ctx.prompt
        assert "deleted" in consenting_ctx.prompt.lower()

    @pytest.mark.asyncio
    async def test_import_names_affected_accounts_and_admits_no_preview(
        self, mock_cache, mock_client, consenting_ctx
    ):
        from src.server import import_transactions

        mock_cache.import_transactions = AsyncMock(return_value=[])
        await import_transactions(plan_id="bud-1", ctx=consenting_ctx)

        prompt = consenting_ctx.prompt
        assert "Checking" in prompt
        assert "NOT known in advance" in prompt

    @pytest.mark.asyncio
    async def test_every_mutating_tool_refuses_without_consent(self, mock_cache, mock_client):
        """No gated tool may apply a change when consent cannot be obtained."""
        from tests.conftest import FakeContext

        import src.server as server

        blocked = FakeContext(supports_elicitation=False)
        calls = {
            "create_account": dict(plan_id="b", name="n", type="checking", balance=1.0),
            "create_transaction": dict(plan_id="b", account_id="a", date="2026-03-15", amount=-1.0),
            "create_transactions": dict(plan_id="b", account_id="a", transactions=[{"date": "2026-03-15", "amount": -1.0}]),
            "update_transaction": dict(plan_id="b", transaction_id="t", amount=-1.0),
            "update_transactions": dict(plan_id="b", transactions=[{"id": "t", "memo": "m"}]),
            "delete_transaction": dict(plan_id="b", transaction_id="t"),
            "import_transactions": dict(plan_id="b"),
            "create_category": dict(plan_id="b", category_group_id="g", name="n"),
            "update_category": dict(plan_id="b", category_id="c", name="n"),
            "create_category_group": dict(plan_id="b", name="n"),
            "update_category_group": dict(plan_id="b", category_group_id="g", name="n"),
            "update_category_for_month": dict(plan_id="b", category_id="c", month="2026-03-01", budgeted=1.0),
            "update_payee": dict(plan_id="b", payee_id="p", name="n"),
            "create_scheduled_transaction": dict(plan_id="b", account_id="a", date="2026-04-01"),
            "update_scheduled_transaction": dict(plan_id="b", scheduled_transaction_id="s", account_id="a", date="2026-04-01"),
            "delete_scheduled_transaction": dict(plan_id="b", scheduled_transaction_id="s"),
        }
        assert len(calls) == 16

        for name, kwargs in calls.items():
            mock_cache.reset_mock()
            result = json.loads(await getattr(server, name)(ctx=blocked, **kwargs))
            assert result.get("reason") == "consent_unavailable", f"{name} was not gated: {result}"
            assert result["applied"] is False
            # Nothing on the cache service was invoked to change anything.
            for attr in dir(mock_cache):
                if attr.startswith(("create_", "update_", "delete_", "import_")):
                    getattr(mock_cache, attr).assert_not_called()

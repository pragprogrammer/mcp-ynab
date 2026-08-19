"""Tests for group-level `internal` exclusion (§1.2).

The regression this guards against: the category-level `internal` flag does not
inherit from the group. Credit Card Payment categories are `internal: false`
inside an `internal: true` group, so a category-level predicate readmits every
one of them — and their `activity` is the payment movement for spending already
counted in the real category, so credit-funded spending would be counted twice.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.models import Category, CategoryGroup, MonthDetail


def InternalCategoryResolver(groups):
    """Imported lazily.

    `src/server/_shared.py` calls `sys.exit(1)` at import time when no token is
    configured, and a module-level import of any `src.server` module would turn
    that into a collection-time abort of the whole session. The rest of the suite
    imports server modules inside test bodies for the same reason.
    """
    from src.server.internal_categories import InternalCategoryResolver as _R

    return _R(groups)

# The shape that makes a category-level predicate wrong: an internal group
# holding several payment categories that are themselves internal=false. The
# count is arbitrary — it only needs to be more than one, so that a predicate
# readmitting them is visibly readmitting a group rather than an edge case.
CREDIT_CARD_COUNT = 4


def _cat(cat_id: str, group_id: str, group_name: str, **kw) -> Category:
    return Category(
        id=cat_id,
        category_group_id=group_id,
        category_group_name=group_name,
        name=kw.pop("name", cat_id),
        **kw,
    )


def _budget_shaped_groups() -> list[CategoryGroup]:
    cc_cats = [
        _cat(f"cc-{i}", "grp-cc", "Credit Card Payments", internal=False, activity=-1000)
        for i in range(CREDIT_CARD_COUNT)
    ]
    return [
        CategoryGroup(
            id="grp-everyday",
            name="Everyday",
            internal=False,
            categories=[
                _cat("cat-a", "grp-everyday", "Everyday", internal=False, activity=-123450)
            ],
        ),
        CategoryGroup(
            id="grp-cc", name="Credit Card Payments", internal=True, categories=cc_cats
        ),
        CategoryGroup(
            id="grp-internal",
            name="Internal Master Category",
            internal=True,
            categories=[
                _cat("inflow", "grp-internal", "Internal Master Category",
                     internal=True, activity=250000)
            ],
        ),
        CategoryGroup(
            id="grp-hidden", name="Hidden Categories", internal=True, categories=[]
        ),
    ]


class TestResolver:
    def test_credit_card_categories_are_internal_via_their_group(self):
        resolver = InternalCategoryResolver(_budget_shaped_groups())
        cc_cats = [
            c
            for g in _budget_shaped_groups()
            if g.id == "grp-cc"
            for c in g.categories
        ]
        assert len(cc_cats) == CREDIT_CARD_COUNT
        assert all(resolver.is_internal(c) for c in cc_cats)
        # ...and the category-level flag would have said otherwise on every one.
        assert all(c.internal is False for c in cc_cats)

    def test_user_categories_are_not_internal(self):
        resolver = InternalCategoryResolver(_budget_shaped_groups())
        assert not resolver.is_internal(
            _cat("cat-a", "grp-everyday", "Everyday", internal=False)
        )

    def test_hidden_categories_group_is_internal(self):
        """The string match misses this group entirely; the flag catches it."""
        groups = [
            CategoryGroup(
                id="grp-hidden",
                name="Hidden Categories",
                internal=True,
                categories=[_cat("h-1", "grp-hidden", "Hidden Categories")],
            )
        ]
        resolver = InternalCategoryResolver(groups)
        assert resolver.is_internal(groups[0].categories[0])

    def test_survives_a_group_rename(self):
        groups = [
            CategoryGroup(
                id="grp-cc",
                name="Tarjetas de crédito",
                internal=True,
                categories=[_cat("cc-1", "grp-cc", "Tarjetas de crédito")],
            )
        ]
        resolver = InternalCategoryResolver(groups)
        assert resolver.is_internal(groups[0].categories[0])

    def test_user_group_cannot_spoof_the_name(self):
        """A user-created group named "Credit Card Payments" is not internal."""
        groups = [
            CategoryGroup(
                id="grp-user",
                name="Credit Card Payments",
                internal=False,
                categories=[_cat("u-1", "grp-user", "Credit Card Payments")],
            )
        ]
        resolver = InternalCategoryResolver(groups)
        assert not resolver.is_internal(groups[0].categories[0])


class TestUnresolvedGroups:
    def test_unmapped_category_falls_back_to_the_legacy_name_check(self):
        """A historical month can name a category absent from the current list."""
        resolver = InternalCategoryResolver(_budget_shaped_groups())
        assert resolver.is_internal(_cat("gone-1", "grp-gone", "Credit Card Payments"))
        assert not resolver.is_internal(_cat("gone-2", "grp-gone", "Groceries"))
        assert resolver.unknown_category_count == 2

    def test_the_two_fallback_reasons_are_counted_separately(self):
        """Routine historical churn must not be reported as a schema regression.

        A 24-month query produces unknown-category misses in bulk. If both
        reasons shared one counter and one log event, a genuine missing-`internal`
        regression would be buried under hundreds of expected misses.
        """
        groups = _budget_shaped_groups()
        groups.append(
            CategoryGroup(
                id="grp_no_flag",
                name="Flagless",
                categories=[_cat("nf-1", "grp_no_flag", "Flagless")],
            )
        )
        resolver = InternalCategoryResolver(groups)

        resolver.is_internal(_cat("gone-1", "grp-gone", "Groceries"))
        resolver.is_internal(_cat("nf-1", "grp_no_flag", "Flagless"))

        assert resolver.unknown_category_count == 1
        assert resolver.missing_flag_count == 1
        assert resolver.fallback_count == 2

    def test_routine_misses_do_not_warn(self, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        resolver = InternalCategoryResolver(_budget_shaped_groups())
        for i in range(200):
            resolver.is_internal(_cat(f"gone-{i}", "grp-gone", "Groceries"))
        resolver.log_fallbacks()

        assert "absent from the current category map" in caplog.text
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING], (
            "expected historical churn was logged as a warning"
        )

    def test_missing_flag_warns(self, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        groups = [
            CategoryGroup(
                id="grp_no_flag",
                name="Flagless",
                categories=[_cat("nf-1", "grp_no_flag", "Flagless")],
            )
        ]
        resolver = InternalCategoryResolver(groups)
        resolver.is_internal(groups[0].categories[0])
        resolver.log_fallbacks()

        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "indicates a schema change" in warnings[0].getMessage()

    def test_absent_internal_flag_falls_back(self):
        """If a future API stops returning `internal`, absent must not read as
        false — that would readmit every payment category."""
        groups = [
            CategoryGroup(
                id="grp-cc",
                name="Credit Card Payments",
                categories=[_cat("cc-1", "grp-cc", "Credit Card Payments")],
            )
        ]
        assert groups[0].internal is None
        resolver = InternalCategoryResolver(groups)
        assert resolver.is_internal(groups[0].categories[0])
        assert resolver.fallback_count == 1

    def test_fallback_logs_the_mechanism_only(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        resolver = InternalCategoryResolver(_budget_shaped_groups())
        resolver.is_internal(_cat("gone-1", "grp-gone", "Secret Vacation Fund"))
        resolver.log_fallbacks()

        assert "legacy group-name exclusion" in caplog.text
        assert "Secret Vacation Fund" not in caplog.text
        assert "gone-1" not in caplog.text


class TestThroughTheAnalyticsTools:
    """The regression that matters: exclusion must survive the wiring."""

    @pytest.fixture
    def analytics_cache(self):
        with (
            patch("src.server._shared.cache", new_callable=AsyncMock) as mock,
            patch("src.server._shared._ensure_db", new_callable=AsyncMock),
        ):
            mock.get_categories = AsyncMock(return_value=_budget_shaped_groups())
            yield mock

    def _month(self) -> MonthDetail:
        cats = [c for g in _budget_shaped_groups() for c in g.categories]
        # A historical category, absent from the current list, excluded via the
        # legacy fallback.
        cats.append(
            _cat("gone-1", "grp-gone", "Credit Card Payments", activity=-45000)
        )
        return MonthDetail(month="2026-08-01", income=250000, categories=cats)

    @pytest.mark.asyncio
    async def test_spending_excludes_every_credit_card_category(
        self, analytics_cache
    ):
        from src.server import get_spending_by_category

        analytics_cache.get_month = AsyncMock(return_value=self._month())
        result = json.loads(
            await get_spending_by_category(plan_id="plan-1", month="2026-08-01")
        )

        assert {c["group"] for c in result["categories"]} == {"Everyday"}
        assert result["total_spent"] == 123.45
        assert len(result["categories"]) == 1

    @pytest.mark.asyncio
    async def test_money_flow_excludes_every_credit_card_category(
        self, analytics_cache
    ):
        from src.server import get_money_flow

        analytics_cache.get_month = AsyncMock(return_value=self._month())
        result = json.loads(
            await get_money_flow(plan_id="plan-1", month="2026-08-01")
        )

        assert [n["name"] for n in result["nodes"]] == ["Income", "Everyday"]
        assert result["total_spent"] == 123.45

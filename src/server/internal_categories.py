"""Which categories are YNAB's own bookkeeping rather than user spending.

Analytics must exclude YNAB-internal categories, or credit-funded spending is
counted twice: a Credit Card Payment category's `activity` is the payment
movement for spending already counted in the real category.

**The predicate is the category's *group's* `internal` flag.** Measured against a
live budget: `Internal Master Category`, `Credit Card Payments`, and
`Hidden Categories` all carry `group.internal = true`, while every Credit Card
Payment *category* carries `internal = false`. The flag does not inherit. Using
the category-level flag would readmit every payment category; matching group
names by string is locale-dependent, breaks on rename, and can be spoofed by a
user-created group of the same name.

Nothing here knows how many such categories exist in any particular budget.
"""

import logging

from src.models import Category, CategoryGroup

logger = logging.getLogger(__name__)

# Fallback only, for a category whose group flag cannot be resolved: a historical
# month can name a category absent from the current category list, and a future
# API could stop returning `internal`.
LEGACY_INTERNAL_GROUP_NAMES = frozenset(
    {"Internal Master Category", "Credit Card Payments"}
)


class InternalCategoryResolver:
    """Decides, per category, whether it belongs to a YNAB-internal group.

    `group.internal` comes from `GET /plans/{id}/categories`; month analytics read
    `GET /plans/{id}/months/{month}`, which carries the category-level flag but
    not the group's. So the map is resolved once from the delta-synced category
    list and applied to the month's categories.

    Two different things can send a category down the legacy fallback, and they
    are counted and reported separately because they mean opposite things:

    * **Absent from the current category list** — routine. A historical month
      names categories deleted since. A 24-month query produces these in bulk.
    * **Present, but the group carries no `internal` flag** — a schema
      regression. `internal` is `required` on `CategoryGroup` in spec 1.86.0, so
      this should never happen, and it is the signal worth acting on.

    Collapsing both into one log event would bury the second under hundreds of
    the first the moment multi-month analytics exist.
    """

    def __init__(self, groups: list[CategoryGroup]):
        self._internal_by_category_id: dict[str, bool | None] = {
            category.id: group.internal
            for group in groups
            for category in group.categories
        }
        self.unknown_category_count = 0
        self.missing_flag_count = 0

    @property
    def fallback_count(self) -> int:
        """Total categories that took the legacy path, for either reason."""
        return self.unknown_category_count + self.missing_flag_count

    def is_internal(self, category: Category) -> bool:
        """True if `category` belongs to a YNAB-internal group.

        A category whose group flag is unknown is not silently treated as "not
        internal", which would readmit exactly what this class exists to
        exclude. It falls back to the legacy group-name check.
        """
        if category.id in self._internal_by_category_id:
            group_internal = self._internal_by_category_id[category.id]
            if group_internal is not None:
                return group_internal
            self.missing_flag_count += 1
        else:
            self.unknown_category_count += 1

        return (category.category_group_name or "") in LEGACY_INTERNAL_GROUP_NAMES

    def log_fallbacks(self) -> None:
        """Report the *mechanism*, once per call. Never category names or amounts."""
        if self.unknown_category_count:
            logger.info(
                "%d categor%s absent from the current category map; "
                "fell back to legacy group-name exclusion. This is expected for "
                "months containing categories deleted since",
                self.unknown_category_count,
                "y is" if self.unknown_category_count == 1 else "ies are",
            )
        if self.missing_flag_count:
            logger.warning(
                "CategoryGroup.internal missing for %d resolved categor%s; "
                "falling back to legacy group-name exclusion. The field is "
                "required by the YNAB API spec, so this indicates a schema change",
                self.missing_flag_count,
                "y" if self.missing_flag_count == 1 else "ies",
            )

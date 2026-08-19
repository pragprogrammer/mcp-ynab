from pydantic import Field

from src.models.common import Milliunit, YNABBaseModel

CATEGORY_DEFAULT_EXCLUDE: set[str] = {
    "original_category_group_id",
    "goal_target_month",
    "goal_creation_month",
    "goal_snoozed_at",
    "goal_needs_whole_amount",
    "goal_day",
    "goal_cadence",
    "goal_cadence_frequency",
    "deleted",
}

CATEGORY_GROUP_DEFAULT_EXCLUDE: set[str] = {"deleted"}


class Category(YNABBaseModel):
    id: str = Field()
    category_group_id: str = Field()
    category_group_name: str | None = Field(default=None)
    name: str = Field()
    hidden: bool = Field(default=False)
    # Required on both models in YNAB spec 1.86.0. Nullable here so an absent
    # flag is distinguishable from a false one: absent must degrade to the legacy
    # group-name check, false must not. Note the flag does NOT inherit — Credit
    # Card Payment categories are internal=false inside an internal=true group,
    # so the *group's* flag is the one that means "not user spending".
    internal: bool | None = Field(default=None)
    original_category_group_id: str | None = Field(default=None)
    note: str | None = Field(default=None)
    budgeted: Milliunit = Field(default=0)
    activity: Milliunit = Field(default=0)
    balance: Milliunit = Field(default=0)
    goal_type: str | None = Field(default=None)
    goal_needs_whole_amount: bool | None = Field(default=None)
    goal_day: int | None = Field(default=None)
    goal_cadence: int | None = Field(default=None)
    goal_cadence_frequency: int | None = Field(default=None)
    goal_creation_month: str | None = Field(default=None)
    goal_target: Milliunit | None = Field(default=None)
    goal_target_month: str | None = Field(default=None)
    goal_target_date: str | None = Field(default=None)
    goal_percentage_complete: int | None = Field(default=None)
    goal_months_to_budget: int | None = Field(default=None)
    goal_under_funded: Milliunit | None = Field(default=None)
    goal_overall_funded: Milliunit | None = Field(default=None)
    goal_overall_left: Milliunit | None = Field(default=None)
    goal_snoozed_at: str | None = Field(default=None)
    deleted: bool = Field(default=False)


class CategoryGroup(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    hidden: bool = Field(default=False)
    internal: bool | None = Field(default=None)
    deleted: bool = Field(default=False)
    categories: list[Category] = Field(default=[])

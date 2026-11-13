from pydantic import Field, computed_field

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


def _cadence_months_and_label(
    cadence: int | None, frequency: int | None
) -> tuple[str, float | None]:
    """Map YNAB goal cadence codes to (goal_period label, months per cycle).

    1=monthly, 2=weekly, 13=yearly (each repeated `frequency` times);
    3-12 = every 2-11 months; 14 = every 2 years. Anything else is "none".
    Weekly cycles are expressed in months as 12/52 per week.
    """
    freq = frequency if frequency and frequency > 0 else 1

    def label(base: str, unit: str, n: int) -> str:
        return base if n == 1 else f"every_{n}_{unit}"

    if cadence == 1:
        return (label("monthly", "months", freq), float(freq))
    if cadence == 2:
        return (label("weekly", "weeks", freq), freq * 12 / 52)
    if cadence == 13:
        return (label("yearly", "years", freq), 12.0 * freq)
    if cadence is not None and 3 <= cadence <= 12:
        return (f"every_{cadence - 1}_months", float(cadence - 1))
    if cadence == 14:
        return ("every_2_years", 24.0)
    return ("none", None)


class Category(YNABBaseModel):
    id: str = Field()
    category_group_id: str = Field()
    category_group_name: str | None = Field(default=None)
    name: str = Field()
    hidden: bool = Field(default=False)
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

    @computed_field
    @property
    def goal_period(self) -> str:
        return _cadence_months_and_label(self.goal_cadence, self.goal_cadence_frequency)[0]

    @computed_field
    @property
    def goal_monthly_equivalent(self) -> Milliunit | None:
        if self.goal_target is None:
            return None
        months = _cadence_months_and_label(self.goal_cadence, self.goal_cadence_frequency)[1]
        if months is None:
            return None
        return round(self.goal_target / months)


class CategoryGroup(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    hidden: bool = Field(default=False)
    deleted: bool = Field(default=False)
    categories: list[Category] = Field(default=[])

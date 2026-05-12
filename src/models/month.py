from pydantic import Field

from src.models.common import Milliunit, YNABBaseModel
from src.models.category import Category

MONTH_DEFAULT_EXCLUDE: set[str] = {"deleted"}


class MonthSummary(YNABBaseModel):
    month: str = Field()
    note: str | None = Field(default=None)
    income: Milliunit = Field(default=0)
    budgeted: Milliunit = Field(default=0)
    activity: Milliunit = Field(default=0)
    to_be_budgeted: Milliunit = Field(default=0)
    age_of_money: int | None = Field(default=None)
    deleted: bool = Field(default=False)


class MonthDetail(YNABBaseModel):
    month: str = Field()
    note: str | None = Field(default=None)
    income: Milliunit = Field(default=0)
    budgeted: Milliunit = Field(default=0)
    activity: Milliunit = Field(default=0)
    to_be_budgeted: Milliunit = Field(default=0)
    age_of_money: int | None = Field(default=None)
    deleted: bool = Field(default=False)
    categories: list[Category] = Field(default=[])

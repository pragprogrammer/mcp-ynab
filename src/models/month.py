from pydantic import Field

from src.models.common import YNABBaseModel
from src.models.category import Category

MONTH_DISPLAY_EXCLUDE = {"deleted"}


class MonthSummary(YNABBaseModel):
    month: str = Field()
    income: int = Field(default=0)
    budgeted: int = Field(default=0)
    activity: int = Field(default=0)
    to_be_budgeted: int = Field(default=0)
    deleted: bool = Field(default=False)


class MonthDetail(YNABBaseModel):
    month: str = Field()
    income: int = Field(default=0)
    budgeted: int = Field(default=0)
    activity: int = Field(default=0)
    to_be_budgeted: int = Field(default=0)
    categories: list[Category] = Field(default=[])

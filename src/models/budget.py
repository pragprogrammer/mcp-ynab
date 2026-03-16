from pydantic import Field

from src.models.common import YNABBaseModel

BUDGET_SUMMARY_DISPLAY_EXCLUDE = {"last_modified_on", "first_month", "last_month"}


class BudgetSummary(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    last_modified_on: str | None = Field(default=None)
    first_month: str | None = Field(default=None)
    last_month: str | None = Field(default=None)


class BudgetDetail(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    last_modified_on: str | None = Field(default=None, serialization_alias="last_modified")
    currency_format: dict | None = Field(default=None)
    date_format: dict | None = Field(default=None)

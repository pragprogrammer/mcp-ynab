from pydantic import Field

from src.models.common import YNABBaseModel

ACCOUNT_DISPLAY_EXCLUDE = {"deleted"}


class Account(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    type: str = Field()
    on_budget: bool = Field(default=False)
    closed: bool = Field(default=False)
    balance: int = Field(default=0)
    cleared_balance: int = Field(default=0)
    uncleared_balance: int = Field(default=0)
    deleted: bool = Field(default=False)

from pydantic import Field

from src.models.common import Milliunit, YNABBaseModel

MONEY_MOVEMENT_DEFAULT_EXCLUDE: set[str] = set()

MONEY_MOVEMENT_GROUP_DEFAULT_EXCLUDE: set[str] = set()


class MoneyMovementGroup(YNABBaseModel):
    id: str = Field()
    group_created_at: str = Field()
    month: str = Field()
    note: str | None = Field(default=None)
    performed_by_user_id: str | None = Field(default=None)


class MoneyMovement(YNABBaseModel):
    id: str = Field()
    month: str | None = Field(default=None)
    moved_at: str | None = Field(default=None)
    note: str | None = Field(default=None)
    money_movement_group_id: str | None = Field(default=None)
    performed_by_user_id: str | None = Field(default=None)
    from_category_id: str | None = Field(default=None)
    to_category_id: str | None = Field(default=None)
    amount: Milliunit = Field(default=0)

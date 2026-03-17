from pydantic import Field

from src.models.common import YNABBaseModel

PAYEE_DISPLAY_EXCLUDE = {"transfer_account_id", "deleted"}


class Payee(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    transfer_account_id: str | None = Field(default=None)
    deleted: bool = Field(default=False)

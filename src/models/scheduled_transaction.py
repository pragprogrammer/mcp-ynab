from pydantic import Field

from src.models.common import Milliunit, YNABBaseModel

SCHEDULED_TRANSACTION_DEFAULT_EXCLUDE: set[str] = {"flag_name", "deleted"}

SCHEDULED_SUBTRANSACTION_DEFAULT_EXCLUDE: set[str] = {"deleted"}


class ScheduledSubtransaction(YNABBaseModel):
    id: str = Field()
    scheduled_transaction_id: str = Field()
    amount: Milliunit = Field(default=0)
    memo: str | None = Field(default=None)
    payee_id: str | None = Field(default=None)
    payee_name: str | None = Field(default=None)
    category_id: str | None = Field(default=None)
    category_name: str | None = Field(default=None)
    transfer_account_id: str | None = Field(default=None)
    deleted: bool = Field(default=False)


class ScheduledTransaction(YNABBaseModel):
    id: str = Field()
    date_first: str | None = Field(default=None)
    date_next: str | None = Field(default=None)
    frequency: str | None = Field(default=None)
    amount: Milliunit = Field(default=0)
    memo: str | None = Field(default=None)
    flag_color: str | None = Field(default=None)
    flag_name: str | None = Field(default=None)
    account_id: str | None = Field(default=None)
    account_name: str | None = Field(default=None)
    payee_id: str | None = Field(default=None)
    payee_name: str | None = Field(default=None)
    category_id: str | None = Field(default=None)
    category_name: str | None = Field(default=None)
    transfer_account_id: str | None = Field(default=None)
    subtransactions: list[ScheduledSubtransaction] = Field(default=[])
    deleted: bool = Field(default=False)

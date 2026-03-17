from pydantic import Field

from src.models.common import YNABBaseModel


class Subtransaction(YNABBaseModel):
    id: str = Field()
    transaction_id: str = Field()
    amount: int = Field(default=0)
    memo: str | None = Field(default=None)
    payee_id: str | None = Field(default=None)
    payee_name: str | None = Field(default=None)
    category_id: str | None = Field(default=None)
    category_name: str | None = Field(default=None)
    deleted: bool = Field(default=False)


# Fields excluded from the transaction display output
TRANSACTION_DISPLAY_EXCLUDE = {
    "account_id", "flag_name", "transfer_account_id", "transfer_transaction_id",
    "import_id", "import_payee_name", "import_payee_name_original",
    "subtransactions", "deleted",
}


class Transaction(YNABBaseModel):
    id: str = Field()
    date: str = Field()
    amount: int = Field(default=0)
    memo: str | None = Field(default=None)
    cleared: str = Field(default="uncleared")
    approved: bool = Field(default=False)
    flag_color: str | None = Field(default=None)
    flag_name: str | None = Field(default=None)
    account_id: str | None = Field(default=None)
    account_name: str | None = Field(default=None, serialization_alias="account")
    payee_id: str | None = Field(default=None)
    payee_name: str | None = Field(default=None, serialization_alias="payee")
    category_id: str | None = Field(default=None)
    category_name: str | None = Field(default=None, serialization_alias="category")
    transfer_account_id: str | None = Field(default=None)
    transfer_transaction_id: str | None = Field(default=None)
    import_id: str | None = Field(default=None)
    import_payee_name: str | None = Field(default=None)
    import_payee_name_original: str | None = Field(default=None)
    subtransactions: list[Subtransaction] = Field(default=[])
    deleted: bool = Field(default=False)


class ScheduledTransaction(YNABBaseModel):
    id: str = Field()
    date_first: str | None = Field(default=None)
    date_next: str | None = Field(default=None)
    frequency: str | None = Field(default=None)
    amount: int = Field(default=0)
    memo: str | None = Field(default=None)
    flag_color: str | None = Field(default=None)
    flag_name: str | None = Field(default=None)
    account_id: str | None = Field(default=None)
    account_name: str | None = Field(default=None, serialization_alias="account")
    payee_id: str | None = Field(default=None)
    payee_name: str | None = Field(default=None, serialization_alias="payee")
    category_id: str | None = Field(default=None)
    category_name: str | None = Field(default=None, serialization_alias="category")
    subtransactions: list[Subtransaction] = Field(default=[])
    deleted: bool = Field(default=False)

# Fields excluded from the scheduled transaction display output
SCHEDULED_TRANSACTION_DISPLAY_EXCLUDE = {
    "date_first", "flag_color", "flag_name", "account_id", "payee_id",
    "category_id", "subtransactions", "deleted",
}

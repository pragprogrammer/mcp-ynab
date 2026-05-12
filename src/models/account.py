from pydantic import Field

from src.models.common import Milliunit, YNABBaseModel

ACCOUNT_DEFAULT_EXCLUDE: set[str] = {
    "direct_import_linked",
    "direct_import_in_error",
    "last_reconciled_at",
    "debt_original_balance",
    "debt_interest_rates",
    "debt_minimum_payments",
    "debt_escrow_amounts",
    "deleted",
}


class Account(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    type: str = Field()
    on_budget: bool = Field(default=False)
    closed: bool = Field(default=False)
    note: str | None = Field(default=None)
    balance: Milliunit = Field(default=0)
    cleared_balance: Milliunit = Field(default=0)
    uncleared_balance: Milliunit = Field(default=0)
    transfer_payee_id: str | None = Field(default=None)
    direct_import_linked: bool = Field(default=False)
    direct_import_in_error: bool = Field(default=False)
    last_reconciled_at: str | None = Field(default=None)
    debt_original_balance: Milliunit | None = Field(default=None)
    debt_interest_rates: dict | None = Field(default=None)
    debt_minimum_payments: dict | None = Field(default=None)
    debt_escrow_amounts: dict | None = Field(default=None)
    deleted: bool = Field(default=False)

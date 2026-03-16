from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class YNABBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class ClearedStatus(StrEnum):
    CLEARED = "cleared"
    UNCLEARED = "uncleared"
    RECONCILED = "reconciled"


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CASH = "cash"
    CREDIT_CARD = "creditCard"
    LINE_OF_CREDIT = "lineOfCredit"
    OTHER_ASSET = "otherAsset"
    OTHER_LIABILITY = "otherLiability"
    MORTGAGE = "mortgage"
    AUTO_LOAN = "autoLoan"
    STUDENT_LOAN = "studentLoan"
    PERSONAL_LOAN = "personalLoan"
    MEDICAL_DEBT = "medicalDebt"
    OTHER_DEBT = "otherDebt"


class Frequency(StrEnum):
    NEVER = "never"
    DAILY = "daily"
    WEEKLY = "weekly"
    EVERY_OTHER_WEEK = "everyOtherWeek"
    TWICE_A_MONTH = "twiceAMonth"
    EVERY_FOUR_WEEKS = "everyFourWeeks"
    MONTHLY = "monthly"
    EVERY_OTHER_MONTH = "everyOtherMonth"
    EVERY_THREE_MONTHS = "everyThreeMonths"
    EVERY_FOUR_MONTHS = "everyFourMonths"
    TWICE_A_YEAR = "twiceAYear"
    YEARLY = "yearly"
    EVERY_OTHER_YEAR = "everyOtherYear"

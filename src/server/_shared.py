import json
import sys
from functools import wraps

import httpx
from mcp.server.fastmcp import FastMCP

from src.cache.service import CacheService
from src.config import Settings
from src.db.engine import init_db
from src.models.account import ACCOUNT_DEFAULT_EXCLUDE, Account
from src.models.category import (
    CATEGORY_DEFAULT_EXCLUDE,
    CATEGORY_GROUP_DEFAULT_EXCLUDE,
    Category,
    CategoryGroup,
)
from src.models.common import YNABBaseModel
from src.models.money_movement import (
    MONEY_MOVEMENT_DEFAULT_EXCLUDE,
    MONEY_MOVEMENT_GROUP_DEFAULT_EXCLUDE,
    MoneyMovement,
    MoneyMovementGroup,
)
from src.models.month import MONTH_DEFAULT_EXCLUDE, MonthDetail, MonthSummary
from src.models.payee import PAYEE_DEFAULT_EXCLUDE, Payee
from src.models.payee_location import PAYEE_LOCATION_DEFAULT_EXCLUDE, PayeeLocation
from src.models.plan import PLAN_DEFAULT_EXCLUDE, PlanDetail, PlanSettings, PlanSummary
from src.models.scheduled_transaction import (
    SCHEDULED_SUBTRANSACTION_DEFAULT_EXCLUDE,
    SCHEDULED_TRANSACTION_DEFAULT_EXCLUDE,
    ScheduledSubtransaction,
    ScheduledTransaction,
)
from src.models.transaction import (
    SUBTRANSACTION_DEFAULT_EXCLUDE,
    TRANSACTION_DEFAULT_EXCLUDE,
    HybridTransaction,
    Subtransaction,
    Transaction,
)
from src.models.user import User
from src.ynab_client import YNABClient, YNABError

try:
    settings = Settings()  # type: ignore[call-arg]
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP("ynab")
client = YNABClient(settings.ynab_api_key, timeout=settings.http_timeout)
cache = CacheService(client, settings)

_db_initialized = False


# Default exclude sets per model. Used when a tool is called without an explicit
# `exclude_fields` argument. See FIELDS.md for the full list per model.
DEFAULT_EXCLUDES: dict[type[YNABBaseModel], set[str]] = {
    Account: ACCOUNT_DEFAULT_EXCLUDE,
    Category: CATEGORY_DEFAULT_EXCLUDE,
    CategoryGroup: CATEGORY_GROUP_DEFAULT_EXCLUDE,
    HybridTransaction: TRANSACTION_DEFAULT_EXCLUDE,
    MoneyMovement: MONEY_MOVEMENT_DEFAULT_EXCLUDE,
    MoneyMovementGroup: MONEY_MOVEMENT_GROUP_DEFAULT_EXCLUDE,
    MonthDetail: MONTH_DEFAULT_EXCLUDE,
    MonthSummary: MONTH_DEFAULT_EXCLUDE,
    Payee: PAYEE_DEFAULT_EXCLUDE,
    PayeeLocation: PAYEE_LOCATION_DEFAULT_EXCLUDE,
    PlanDetail: PLAN_DEFAULT_EXCLUDE,
    PlanSettings: set(),
    PlanSummary: PLAN_DEFAULT_EXCLUDE,
    ScheduledSubtransaction: SCHEDULED_SUBTRANSACTION_DEFAULT_EXCLUDE,
    ScheduledTransaction: SCHEDULED_TRANSACTION_DEFAULT_EXCLUDE,
    Subtransaction: SUBTRANSACTION_DEFAULT_EXCLUDE,
    Transaction: TRANSACTION_DEFAULT_EXCLUDE,
    User: set(),
}


def dollars_to_milliunits(amount: float) -> int:
    """Convert a dollar amount to YNAB milliunits (1000 = $1.00)."""
    return round(amount * 1000)


# Nested default excludes: when a parent model contains a list of nested models,
# the nested model's default excludes need to be applied explicitly because
# Pydantic's model_dump(exclude=set) only handles top-level fields.
NESTED_DEFAULT_EXCLUDES: dict[type[YNABBaseModel], dict[str, type[YNABBaseModel]]] = {
    CategoryGroup: {"categories": Category},
    MonthDetail: {"categories": Category},
}


def _resolve_exclude(
    model_class: type[YNABBaseModel], exclude_fields: list[str] | None
) -> set[str] | dict[str, object]:
    """Pick the exclude for a model.

    Top-level uses the caller's exclude_fields if provided, otherwise the model
    default. Nested defaults (per NESTED_DEFAULT_EXCLUDES) always apply so the
    nested-model defaults aren't dropped when a caller customizes top-level.
    """
    if exclude_fields is None:
        top_level: set[str] = DEFAULT_EXCLUDES.get(model_class, set())
    else:
        top_level = set(exclude_fields)

    nested = NESTED_DEFAULT_EXCLUDES.get(model_class)
    if not nested:
        return top_level

    exclude: dict[str, object] = {f: True for f in top_level}
    for field_name, nested_class in nested.items():
        nested_default = DEFAULT_EXCLUDES.get(nested_class, set())
        if nested_default:
            exclude[field_name] = {"__all__": nested_default}
    return exclude


def serialize(model, *, exclude_fields: list[str] | None = None) -> str:
    """Serialize a Pydantic model to a JSON string.

    By default, excludes the model's standard noisy/rarely-used fields. Pass
    `exclude_fields=[]` to return all fields, or a custom list to override.
    """
    exclude = _resolve_exclude(type(model), exclude_fields)
    return json.dumps(
        model.model_dump(by_alias=True, mode="json", exclude=exclude), indent=2
    )


def serialize_list(models, *, exclude_fields: list[str] | None = None) -> str:
    """Serialize a list of Pydantic models to a JSON string.

    By default, excludes the model's standard noisy/rarely-used fields. Pass
    `exclude_fields=[]` to return all fields, or a custom list to override.
    """
    if not models:
        return "[]"
    exclude = _resolve_exclude(type(models[0]), exclude_fields)
    return json.dumps(
        [m.model_dump(by_alias=True, mode="json", exclude=exclude) for m in models],
        indent=2,
    )


async def _ensure_db():
    global _db_initialized
    if not _db_initialized:
        await init_db(settings.cache_db_path)
        _db_initialized = True


def handle_errors(func):
    """Decorator that catches YNAB and HTTP errors and returns friendly messages."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            await _ensure_db()
            return await func(*args, **kwargs)
        except YNABError as e:
            return json.dumps({"error": e.message, "error_id": e.error_id, "status_code": e.status_code})
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"})
        except httpx.RequestError as e:
            return json.dumps({"error": f"Request failed: {e}"})

    return wrapper

from mcp.server.mcpserver import Context

from src.security import consent, diff
from src.server import _shared
from src.server._shared import dollars_to_milliunits, serialize, serialize_list


async def _scheduled_preimage(scheduled_transaction_id: str, plan_id: str) -> dict:
    """Read a scheduled transaction straight from the API, bypassing the cache.

    The write payload calls the next occurrence "date" while the API reports it
    as "date_next"; mirroring it under both names lets the diff line up the field
    the caller is actually changing. Both values come from the API response.
    """
    txn = (
        await _shared.client.get_scheduled_transaction(scheduled_transaction_id, plan_id)
    ).model_dump()
    if txn.get("date_next") is not None:
        txn.setdefault("date", txn["date_next"])
    return txn


@_shared.mcp.tool()
@_shared.handle_errors
async def list_scheduled_transactions(
    plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """List all scheduled (recurring) transactions.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_scheduled_transactions(plan_id)
    return serialize_list(transactions, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_scheduled_transaction(
    scheduled_transaction_id: str,
    plan_id: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get a single scheduled transaction.

    Args:
        scheduled_transaction_id: The scheduled transaction ID
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    txn = await _shared.cache.get_scheduled_transaction(scheduled_transaction_id, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mutating_tool()
@_shared.handle_errors
async def create_scheduled_transaction(
    plan_id: str,
    account_id: str,
    date: str,
    amount: float | None = None,
    payee_id: str | None = None,
    payee_name: str | None = None,
    category_id: str | None = None,
    memo: str | None = None,
    flag_color: str | None = None,
    frequency: str | None = None,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a scheduled transaction. Requires human confirmation.

    A scheduled transaction is a transaction with a future date.

    Splits are not supported on this endpoint. Date must be in the future, no more
    than 5 years out.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        account_id: The account ID for this scheduled transaction
        date: Future date in YYYY-MM-DD format (no more than 5 years out)
        amount: Amount in dollars (negative for outflow, positive for inflow). e.g. -50.25 for spending $50.25
        payee_id: Payee ID (use list_payees to find available IDs). For account transfers, use the target account's transfer_payee_id.
        payee_name: Payee name. If payee_id is null, this resolves to an existing payee or creates a new one.
        category_id: Category ID. Credit Card Payment categories are not permitted.
        memo: Memo/note (max 500 chars)
        flag_color: 'red', 'orange', 'yellow', 'green', 'blue', 'purple', or null
        frequency: One of 'never', 'daily', 'weekly', 'everyOtherWeek', 'twiceAMonth',
            'every4Weeks', 'monthly', 'everyOtherMonth', 'every3Months', 'every4Months',
            'twiceAYear', 'yearly', 'everyOtherYear'
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    scheduled: dict = {
        "account_id": account_id,
        "date": date,
    }
    if amount is not None:
        scheduled["amount"] = dollars_to_milliunits(amount)
    if payee_id is not None:
        scheduled["payee_id"] = payee_id
    if payee_name is not None:
        scheduled["payee_name"] = payee_name
    if category_id is not None:
        scheduled["category_id"] = category_id
    if memo is not None:
        scheduled["memo"] = memo
    if flag_color is not None:
        scheduled["flag_color"] = flag_color
    if frequency is not None:
        scheduled["frequency"] = frequency

    fingerprint = await consent.confirm(
        ctx,
        action="Create scheduled transaction",
        plan_id=plan_id,
        payload=scheduled,
        body=(
            "This recurring transaction will be created:\n"
            f"  {diff.describe_scheduled_transaction(scheduled)}\n\n"
            "Exact fields sent to YNAB:\n"
            f"{diff.render_new_object(scheduled)}"
        ),
    )
    consent.assert_unchanged(scheduled, fingerprint)
    txn = await _shared.cache.create_scheduled_transaction(scheduled, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mutating_tool()
@_shared.handle_errors
async def update_scheduled_transaction(
    plan_id: str,
    scheduled_transaction_id: str,
    account_id: str,
    date: str,
    amount: float | None = None,
    payee_id: str | None = None,
    payee_name: str | None = None,
    category_id: str | None = None,
    memo: str | None = None,
    flag_color: str | None = None,
    frequency: str | None = None,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update a scheduled transaction. Requires human confirmation.

    The API requires account_id and date on every update. Splits are not supported on
    this endpoint. Date must be in the future, no more than 5 years out.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        scheduled_transaction_id: The scheduled transaction ID to update
        account_id: The account ID for this scheduled transaction (required)
        date: Future date in YYYY-MM-DD format (required, no more than 5 years out)
        amount: Amount in dollars (negative for outflow, positive for inflow)
        payee_id: Payee ID. For account transfers, use the target account's transfer_payee_id.
        payee_name: Payee name (resolves to existing or creates a new payee)
        category_id: Category ID. Credit Card Payment categories are not permitted.
        memo: Memo/note (max 500 chars)
        flag_color: 'red', 'orange', 'yellow', 'green', 'blue', 'purple', or null
        frequency: One of 'never', 'daily', 'weekly', 'everyOtherWeek', 'twiceAMonth',
            'every4Weeks', 'monthly', 'everyOtherMonth', 'every3Months', 'every4Months',
            'twiceAYear', 'yearly', 'everyOtherYear'
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    scheduled: dict = {
        "account_id": account_id,
        "date": date,
    }
    if amount is not None:
        scheduled["amount"] = dollars_to_milliunits(amount)
    if payee_id is not None:
        scheduled["payee_id"] = payee_id
    if payee_name is not None:
        scheduled["payee_name"] = payee_name
    if category_id is not None:
        scheduled["category_id"] = category_id
    if memo is not None:
        scheduled["memo"] = memo
    if flag_color is not None:
        scheduled["flag_color"] = flag_color
    if frequency is not None:
        scheduled["frequency"] = frequency

    before = await _scheduled_preimage(scheduled_transaction_id, plan_id)
    fingerprint = await consent.confirm(
        ctx,
        action="Update scheduled transaction",
        plan_id=plan_id,
        subject=diff.describe_scheduled_transaction(before),
        before=before,
        payload=scheduled,
    )
    consent.assert_unchanged(scheduled, fingerprint)
    txn = await _shared.cache.update_scheduled_transaction(
        scheduled_transaction_id, scheduled, plan_id
    )
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mutating_tool()
@_shared.handle_errors
async def delete_scheduled_transaction(
    scheduled_transaction_id: str,
    plan_id: str,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Delete a scheduled transaction. Requires human confirmation.

    Args:
        scheduled_transaction_id: The scheduled transaction ID to delete
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    before = await _scheduled_preimage(scheduled_transaction_id, plan_id)
    target = {
        "scheduled_transaction_id": scheduled_transaction_id,
        "plan_id": plan_id,
    }
    fingerprint = await consent.confirm(
        ctx,
        action="DELETE scheduled transaction",
        plan_id=plan_id,
        payload=target,
        body=(
            "This recurring transaction will be permanently deleted:\n"
            f"  {diff.describe_scheduled_transaction(before)}"
        ),
    )
    consent.assert_unchanged(target, fingerprint)
    txn = await _shared.cache.delete_scheduled_transaction(scheduled_transaction_id, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)

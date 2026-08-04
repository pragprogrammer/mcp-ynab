from src.server import _shared
from src.server._shared import dollars_to_milliunits, serialize, serialize_list


@_shared.mcp.tool()
@_shared.handle_errors
async def list_accounts(
    plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """List all accounts in a plan.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from each account.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    accounts = await _shared.cache.get_accounts(plan_id)
    return serialize_list(accounts, exclude_fields=exclude_fields)


@_shared.write_tool()
@_shared.handle_errors
async def create_account(
    plan_id: str,
    name: str,
    type: str,
    balance: float,
    exclude_fields: list[str] | None = None,
) -> str:
    """Create a new account.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        name: The name of the account
        type: The type of account ('checking', 'savings', 'cash', 'creditCard', 'lineOfCredit', 'otherAsset', 'otherLiability', 'mortgage', 'autoLoan', 'studentLoan', 'personalLoan', 'medicalDebt', 'otherDebt')
        balance: The current balance in dollars (e.g. 1000.00)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    account = {
        "name": name,
        "type": type,
        "balance": dollars_to_milliunits(balance),
    }
    acct = await _shared.cache.create_account(account, plan_id)
    return serialize(acct, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_account(
    account_id: str, plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """Get details for a specific account.

    Args:
        account_id: The account ID
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    account = await _shared.cache.get_account(account_id, plan_id)
    return serialize(account, exclude_fields=exclude_fields)

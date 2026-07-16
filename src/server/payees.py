from src.server import _shared
from src.server._shared import serialize, serialize_list


@_shared.mcp.tool()
@_shared.handle_errors
async def list_payees(
    plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """List all payees in a plan.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from each payee.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payees = await _shared.cache.get_payees(plan_id)
    return serialize_list(payees, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_payee(
    payee_id: str, plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """Get a single payee.

    Args:
        payee_id: The payee ID
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payee = await _shared.cache.get_payee(payee_id, plan_id)
    return serialize(payee, exclude_fields=exclude_fields)


@_shared.write_tool()
@_shared.handle_errors
async def create_payee(
    plan_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Create a new payee.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        name: The name of the new payee (max 500 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payee = await _shared.cache.create_payee({"name": name}, plan_id)
    return serialize(payee, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_payee(
    plan_id: str,
    payee_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Update a payee.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        payee_id: The payee ID to update
        name: New name for the payee (max 500 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payee = await _shared.cache.update_payee(payee_id, {"name": name}, plan_id)
    return serialize(payee, exclude_fields=exclude_fields)

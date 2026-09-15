from mcp.server.mcpserver import Context

from src.security import consent
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


@_shared.mcp.tool()
@_shared.handle_errors
async def update_payee(
    plan_id: str,
    payee_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update a payee. Requires human confirmation.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        payee_id: The payee ID to update
        name: New name for the payee (max 500 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payload = {"name": name}
    # Straight from the API, not the cache: a stale name would be a false "before".
    before = (await _shared.client.get_payee(payee_id, plan_id)).model_dump()
    fingerprint = await consent.confirm(
        ctx,
        action="Rename payee",
        plan_id=plan_id,
        subject=f'payee "{before.get("name")}" ({payee_id})',
        before=before,
        payload=payload,
    )
    consent.assert_unchanged(payload, fingerprint)
    payee = await _shared.cache.update_payee(payee_id, payload, plan_id)
    return serialize(payee, exclude_fields=exclude_fields)

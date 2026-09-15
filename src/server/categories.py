from mcp.server.mcpserver import Context

from src.security import consent, diff
from src.server import _shared
from src.server._shared import dollars_to_milliunits, serialize, serialize_list


async def _category_group_preimage(category_group_id: str, plan_id: str) -> dict:
    """Read a category group straight from the API, bypassing the cache.

    There is no single-group endpoint, so this pulls the group list and picks the
    one being changed. One extra call on a rare operation buys a "before" that is
    actually true rather than one assembled from whatever the model asserted.
    """
    groups, _knowledge = await _shared.client.get_categories(plan_id)
    for group in groups:
        if group.id == category_group_id:
            return group.model_dump(exclude={"categories"})
    return {}


_FIELDS_DOC = (
    "Optional list of field names to exclude from the response. "
    "If omitted, the model's default exclude list is used (see FIELDS.md). "
    "Pass [] to return all fields. Pass a custom list to override the default."
)


@_shared.mcp.tool()
@_shared.handle_errors
async def list_categories(
    plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """List all categories grouped by category group.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from each category group.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    groups = await _shared.cache.get_categories(plan_id)
    return serialize_list(groups, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_category(
    category_id: str, plan_id: str, exclude_fields: list[str] | None = None
) -> str:
    """Get a single category. Amounts are specific to the current plan month (UTC).

    Args:
        category_id: The category ID
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    cat = await _shared.cache.get_category(category_id, plan_id)
    return serialize(cat, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def create_category(
    plan_id: str,
    category_group_id: str,
    name: str,
    note: str | None = None,
    goal_target: float | None = None,
    goal_target_date: str | None = None,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a new category in a category group. Requires human confirmation.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        category_group_id: The category group ID to create the category in
        name: The name of the new category
        note: Optional note for the category
        goal_target: Optional goal target amount in dollars. If specified and no goal exists, a monthly 'Needed for Spending' goal will be created.
        goal_target_date: Optional goal target date in ISO format (e.g. '2026-12-01')
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    category: dict = {
        "category_group_id": category_group_id,
        "name": name,
    }
    if note is not None:
        category["note"] = note
    if goal_target is not None:
        category["goal_target"] = dollars_to_milliunits(goal_target)
    if goal_target_date is not None:
        category["goal_target_date"] = goal_target_date

    fingerprint = await consent.confirm(
        ctx, action="Create category", plan_id=plan_id, payload=category
    )
    consent.assert_unchanged(category, fingerprint)
    cat = await _shared.cache.create_category(category, plan_id)
    return serialize(cat, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_category(
    plan_id: str,
    category_id: str,
    name: str | None = None,
    note: str | None = None,
    category_group_id: str | None = None,
    goal_target: float | None = None,
    goal_target_date: str | None = None,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update a category. Requires human confirmation.

    Only provide the fields you want to change.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        category_id: The category ID to update
        name: New name for the category
        note: New note for the category
        category_group_id: Move category to a different category group
        goal_target: Goal target amount in dollars. If specified and no goal exists, a monthly 'Needed for Spending' goal will be created.
        goal_target_date: Goal target date in ISO format (e.g. '2026-12-01')
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    category: dict = {}
    if name is not None:
        category["name"] = name
    if note is not None:
        category["note"] = note
    if category_group_id is not None:
        category["category_group_id"] = category_group_id
    if goal_target is not None:
        category["goal_target"] = dollars_to_milliunits(goal_target)
    if goal_target_date is not None:
        category["goal_target_date"] = goal_target_date

    before = (await _shared.client.get_category(category_id, plan_id)).model_dump()
    fingerprint = await consent.confirm(
        ctx,
        action="Update category",
        plan_id=plan_id,
        subject=f'category "{before.get("name")}" ({category_id})',
        before=before,
        payload=category,
    )
    consent.assert_unchanged(category, fingerprint)
    cat = await _shared.cache.update_category(category_id, category, plan_id)
    return serialize(cat, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def create_category_group(
    plan_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a new category group. Requires human confirmation.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        name: The name of the category group (max 50 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payload = {"name": name}
    fingerprint = await consent.confirm(
        ctx, action="Create category group", plan_id=plan_id, payload=payload
    )
    consent.assert_unchanged(payload, fingerprint)
    group = await _shared.cache.create_category_group(payload, plan_id)
    return serialize(group, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_category_group(
    plan_id: str,
    category_group_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update a category group. Requires human confirmation.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        category_group_id: The category group ID to update
        name: New name for the category group (max 50 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payload = {"name": name}
    before = await _category_group_preimage(category_group_id, plan_id)
    fingerprint = await consent.confirm(
        ctx,
        action="Rename category group",
        plan_id=plan_id,
        subject=f'category group "{before.get("name", "(not found)")}" ({category_group_id})',
        before=before,
        payload=payload,
    )
    consent.assert_unchanged(payload, fingerprint)
    group = await _shared.cache.update_category_group(
        category_group_id, payload, plan_id
    )
    return serialize(group, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_category_for_month(
    category_id: str,
    month: str,
    plan_id: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get category details for a specific month.

    Args:
        category_id: The category ID
        month: Month in YYYY-MM-DD format (use first of month, e.g. '2026-03-01')
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    cat = await _shared.cache.get_category_for_month(month, category_id, plan_id)
    return serialize(cat, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_category_for_month(
    category_id: str,
    month: str,
    budgeted: float,
    plan_id: str,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update the budgeted amount for a category in a month. Requires human confirmation.

    Args:
        category_id: The category ID
        month: Month in YYYY-MM-DD format (use first of month, e.g. '2026-03-01')
        budgeted: Budgeted amount in dollars (e.g. 500.00)
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    payload = {"budgeted": dollars_to_milliunits(budgeted)}
    before = (
        await _shared.client.get_category_for_month(month, category_id, plan_id)
    ).model_dump()
    fingerprint = await consent.confirm(
        ctx,
        action=f"Set budgeted amount for {month}",
        plan_id=plan_id,
        subject=(
            f'category "{before.get("name")}" ({category_id}) — '
            f"budgeted {diff.format_money(before.get('budgeted'))}, "
            f"activity {diff.format_money(before.get('activity'))}, "
            f"balance {diff.format_money(before.get('balance'))}"
        ),
        before=before,
        payload=payload,
    )
    consent.assert_unchanged(payload, fingerprint)
    cat = await _shared.cache.update_category_for_month(
        month, category_id, payload["budgeted"], plan_id
    )
    return serialize(cat, exclude_fields=exclude_fields)

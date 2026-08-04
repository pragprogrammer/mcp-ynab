from datetime import date

from src.server import _shared
from src.server._shared import dollars_to_milliunits, serialize, serialize_list

_FIELDS_DOC = (
    "Optional list of field names to exclude from the response. "
    "If omitted, the model's default exclude list is used (see FIELDS.md). "
    "Pass [] to return all fields. Pass a custom list to override the default."
)

AUTO_ASSIGN_SKIP_GROUPS = {
    "Internal Master Category",
    "Credit Card Payments",
    "Hidden Categories",
}


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
) -> str:
    """Create a new category in a category group.

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
) -> str:
    """Update a category. Only provide the fields you want to change.

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

    cat = await _shared.cache.update_category(category_id, category, plan_id)
    return serialize(cat, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def create_category_group(
    plan_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Create a new category group.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        name: The name of the category group (max 50 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    group = await _shared.cache.create_category_group({"name": name}, plan_id)
    return serialize(group, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_category_group(
    plan_id: str,
    category_group_id: str,
    name: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Update a category group.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        category_group_id: The category group ID to update
        name: New name for the category group (max 50 characters)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    group = await _shared.cache.update_category_group(
        category_group_id, {"name": name}, plan_id
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
) -> str:
    """Update the budgeted amount for a category in a specific month.

    Args:
        category_id: The category ID
        month: Month in YYYY-MM-DD format (use first of month, e.g. '2026-03-01')
        budgeted: Budgeted amount in dollars (e.g. 500.00)
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    cat = await _shared.cache.update_category_for_month(
        month, category_id, dollars_to_milliunits(budgeted), plan_id
    )
    return serialize(cat, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def auto_assign_monthly_targets(plan_id: str, month: str = "current") -> str:
    """Assign budgets to all categories based on their goal targets.

    Mirrors YNAB's Auto-Assign -> Monthly Targets button. For every category
    that has a goal_target set, assigns the goal amount as the budgeted value
    for the given month. Skips hidden, deleted, and internal groups
    (Internal Master Category, Credit Card Payments, Hidden Categories).

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        month: Month in YYYY-MM-DD format (e.g. '2026-05-01') or 'current'. Defaults to current month.
    """
    import json

    if month == "current":
        today = date.today()
        month = today.replace(day=1).strftime("%Y-%m-%d")

    groups = await _shared.cache.get_categories(plan_id)
    assignments = []
    for group in groups:
        if group.name in AUTO_ASSIGN_SKIP_GROUPS or group.hidden or group.deleted:
            continue
        for cat in group.categories:
            if cat.hidden or cat.deleted or not cat.goal_target:
                continue
            updated = await _shared.cache.update_category_for_month(
                month, cat.id, cat.goal_target, plan_id
            )
            assignments.append({
                "name": updated.name,
                "group": group.name,
                "budgeted": updated.budgeted / 1000,
            })

    total = sum(a["budgeted"] for a in assignments)
    return json.dumps(
        {
            "month": month,
            "categories_assigned": len(assignments),
            "total_budgeted": round(total, 2),
            "assignments": assignments,
        },
        indent=2,
    )

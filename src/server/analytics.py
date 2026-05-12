import json
from datetime import date

from src.models.common import milliunits_to_dollars
from src.server import _shared

MONEY_FLOW_EXCLUDE_GROUPS = {"Internal Master Category", "Credit Card Payments"}


@_shared.mcp.tool()
@_shared.handle_errors
async def get_money_flow(plan_id: str, month: str = "current") -> str:
    """Build Sankey chart data showing money flow from income sources to spending category groups.

    Returns nodes and index-based links suitable for Sankey/flow visualizations.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        month: Month in YYYY-MM-DD format (first of month, e.g. '2026-03-01') or 'current'
    """
    if month == "current":
        today = date.today()
        month = today.replace(day=1).strftime("%Y-%m-%d")

    # Fetch month detail (has categories with activity and income total)
    month_detail = await _shared.cache.get_month(month, plan_id)

    # Group categories by category_group_name and sum activity
    group_activity: dict[str, int] = {}
    for cat in month_detail.categories:
        group_name = cat.category_group_name or "Uncategorized"
        if group_name in MONEY_FLOW_EXCLUDE_GROUPS:
            continue
        group_activity[group_name] = group_activity.get(group_name, 0) + cat.activity

    # Filter out groups with zero activity
    group_activity = {name: activity for name, activity in group_activity.items() if activity != 0}

    # Build nodes: index 0 is Income, then one per category group
    nodes = [{"name": "Income"}]
    links = []
    total_spent_mu = 0

    for group_name, activity_mu in sorted(group_activity.items()):
        abs_mu = abs(activity_mu)
        total_spent_mu += abs_mu
        target_index = len(nodes)
        nodes.append({"name": group_name})
        links.append({"source": 0, "target": target_index, "value": milliunits_to_dollars(abs_mu)})

    result = {
        "month": month,
        "total_income": milliunits_to_dollars(abs(month_detail.income)),
        "total_spent": milliunits_to_dollars(total_spent_mu),
        "nodes": nodes,
        "links": links,
    }
    return json.dumps(result, indent=2)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_spending_by_category(plan_id: str, month: str = "current") -> str:
    """Get per-category spending breakdown for a month, with budget vs actual comparison.

    Returns categories sorted by spending (highest first), grouped by category group,
    with budgeted, spent, balance, and percentage of total spending.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        month: Month in YYYY-MM-DD format (first of month, e.g. '2026-03-01') or 'current'
    """
    if month == "current":
        today = date.today()
        month = today.replace(day=1).strftime("%Y-%m-%d")

    month_detail = await _shared.cache.get_month(month, plan_id)

    # Collect categories with non-zero activity, excluding internal groups
    categories = []
    total_spent_mu = 0
    for cat in month_detail.categories:
        group_name = cat.category_group_name or "Uncategorized"
        if group_name in MONEY_FLOW_EXCLUDE_GROUPS:
            continue
        if cat.activity == 0:
            continue
        spent_mu = abs(cat.activity)
        total_spent_mu += spent_mu
        categories.append({
            "group": group_name,
            "name": cat.name,
            "budgeted_mu": cat.budgeted,
            "spent_mu": spent_mu,
            "balance_mu": cat.balance,
        })

    # Sort by spending (highest first) and compute percentages
    categories.sort(key=lambda c: c["spent_mu"], reverse=True)
    result_cats = []
    for c in categories:
        pct = round(c["spent_mu"] / total_spent_mu * 100, 1) if total_spent_mu > 0 else 0.0
        result_cats.append({
            "group": c["group"],
            "name": c["name"],
            "budgeted": milliunits_to_dollars(c["budgeted_mu"]),
            "spent": milliunits_to_dollars(c["spent_mu"]),
            "balance": milliunits_to_dollars(c["balance_mu"]),
            "pct_of_total": pct,
        })

    result = {
        "month": month,
        "total_spent": milliunits_to_dollars(total_spent_mu),
        "categories": result_cats,
    }
    return json.dumps(result, indent=2)

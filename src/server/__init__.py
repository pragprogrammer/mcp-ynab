from src.server._shared import mcp

# Import domain modules to trigger @mcp.tool() registration
from src.server.user import get_user
from src.server.plans import list_plans, get_plan, get_plan_settings
from src.server.accounts import list_accounts, create_account, get_account
from src.server.transactions import (
    list_transactions, get_transaction, get_transactions_by_account,
    get_transactions_by_category, get_transactions_by_month, get_transactions_by_payee,
    search_transactions, create_transaction, create_transactions,
    update_transaction, delete_transaction, update_transactions,
    import_transactions,
)
from src.server.categories import (
    list_categories, get_category, create_category, update_category,
    create_category_group, update_category_group,
    get_category_for_month, update_category_for_month,
    auto_assign_monthly_targets,
)
from src.server.payees import list_payees, get_payee, update_payee
from src.server.payee_locations import (
    list_payee_locations, get_payee_location, get_payee_locations_by_payee,
)
from src.server.money_movements import (
    list_money_movements, get_money_movements_for_month,
    list_money_movement_groups, get_money_movement_groups_for_month,
)
from src.server.months import list_months, get_month
from src.server.scheduled import (
    list_scheduled_transactions, get_scheduled_transaction,
    create_scheduled_transaction, update_scheduled_transaction,
    delete_scheduled_transaction,
)
from src.server.analytics import get_money_flow, get_spending_by_category

__all__ = [
    "get_user",
    "list_plans", "get_plan", "get_plan_settings",
    "list_accounts", "create_account", "get_account",
    "list_transactions", "get_transaction", "get_transactions_by_account",
    "get_transactions_by_category", "get_transactions_by_month", "get_transactions_by_payee",
    "search_transactions", "create_transaction", "create_transactions",
    "update_transaction", "delete_transaction", "update_transactions",
    "import_transactions",
    "list_categories", "get_category", "create_category", "update_category",
    "create_category_group", "update_category_group",
    "get_category_for_month", "update_category_for_month",
    "auto_assign_monthly_targets",
    "list_payees", "get_payee", "update_payee",
    "list_payee_locations", "get_payee_location", "get_payee_locations_by_payee",
    "list_money_movements", "get_money_movements_for_month",
    "list_money_movement_groups", "get_money_movement_groups_for_month",
    "list_months", "get_month",
    "list_scheduled_transactions", "get_scheduled_transaction",
    "create_scheduled_transaction", "update_scheduled_transaction",
    "delete_scheduled_transaction",
    "get_money_flow", "get_spending_by_category",
    "main",
]


def main():
    mcp.run(transport="stdio")

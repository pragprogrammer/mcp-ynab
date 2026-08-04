import httpx
from typing import Any

from src.models import (
    Account,
    PlanDetail,
    PlanSettings,
    PlanSummary,
    Category,
    CategoryGroup,
    MonthDetail,
    MonthSummary,
    MoneyMovement,
    MoneyMovementGroup,
    Payee,
    PayeeLocation,
    HybridTransaction,
    ScheduledTransaction,
    Transaction,
    User,
)


class YNABError(Exception):
    """Raised when the YNAB API returns an error."""

    def __init__(self, status_code: int, error_id: str, message: str):
        self.status_code = status_code
        self.error_id = error_id
        self.message = message
        super().__init__(f"YNAB API error {status_code} ({error_id}): {message}")


class YNABClient:
    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, api_key: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def _handle_error(self, response: httpx.Response) -> None:
        """Parse YNAB error response and raise a descriptive exception."""
        try:
            body = response.json()
            error = body.get("error", {})
            raise YNABError(
                status_code=response.status_code,
                error_id=error.get("id", "unknown"),
                message=error.get("detail", response.text),
            )
        except (ValueError, KeyError):
            response.raise_for_status()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        response = await self._client.get(path, params=params)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    async def _post(self, path: str, json: dict[str, Any]) -> dict:
        response = await self._client.post(path, json=json)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    async def _patch(self, path: str, json: dict[str, Any]) -> dict:
        response = await self._client.patch(path, json=json)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    async def _put(self, path: str, json: dict[str, Any]) -> dict:
        response = await self._client.put(path, json=json)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    async def _delete(self, path: str) -> dict:
        response = await self._client.delete(path)
        if response.is_error:
            self._handle_error(response)
        return response.json()

    @staticmethod
    def _add_knowledge(params: dict | None, knowledge: int | None) -> dict | None:
        if knowledge is not None:
            params = params or {}
            params["last_knowledge_of_server"] = knowledge
        return params

    # ── User ─────────────────────────────────────────────────

    async def get_user(self) -> User:
        data = await self._get("/user")
        return User.model_validate(data["data"]["user"])

    # ── Budgets ──────────────────────────────────────────────

    async def get_plans(self) -> list[PlanSummary]:
        data = await self._get("/plans")
        return [PlanSummary.model_validate(b) for b in data["data"]["plans"]]

    async def get_plan(self, plan_id: str) -> PlanDetail:
        data = await self._get(f"/plans/{plan_id}")
        return PlanDetail.model_validate(data["data"]["plan"])

    async def get_plan_settings(self, plan_id: str) -> PlanSettings:
        data = await self._get(f"/plans/{plan_id}/settings")
        return PlanSettings.model_validate(data["data"]["settings"])

    # ── Accounts ─────────────────────────────────────────────

    async def get_accounts(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[Account], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/accounts", params=params)
        accounts = [Account.model_validate(a) for a in data["data"]["accounts"]]
        knowledge = data["data"]["server_knowledge"]
        return accounts, knowledge

    async def create_account(self, account: dict, plan_id: str) -> Account:
        data = await self._post(
            f"/plans/{plan_id}/accounts",
            json={"account": account},
        )
        return Account.model_validate(data["data"]["account"])

    async def get_account(self, account_id: str, plan_id: str) -> Account:
        data = await self._get(f"/plans/{plan_id}/accounts/{account_id}")
        return Account.model_validate(data["data"]["account"])

    # ── Transactions ─────────────────────────────────────────

    async def get_transactions(
        self,
        plan_id: str,
        since_date: str | None = None,
        type: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> tuple[list[Transaction], int]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if type:
            params["type"] = type
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(f"/plans/{plan_id}/transactions", params=params or None)
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_transaction(self, transaction_id: str, plan_id: str) -> Transaction:
        data = await self._get(f"/plans/{plan_id}/transactions/{transaction_id}")
        return Transaction.model_validate(data["data"]["transaction"])

    async def get_transactions_by_account(
        self,
        account_id: str,
        plan_id: str,
        since_date: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> tuple[list[Transaction], int]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/plans/{plan_id}/accounts/{account_id}/transactions",
            params=params or None,
        )
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_transactions_by_category(
        self,
        category_id: str,
        plan_id: str,
        since_date: str | None = None,
        type: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> list[HybridTransaction]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if type:
            params["type"] = type
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/plans/{plan_id}/categories/{category_id}/transactions",
            params=params or None,
        )
        return [HybridTransaction.model_validate(t) for t in data["data"]["transactions"]]

    async def get_transactions_by_month(
        self,
        month: str,
        plan_id: str,
        since_date: str | None = None,
        type: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> tuple[list[Transaction], int]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if type:
            params["type"] = type
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/plans/{plan_id}/months/{month}/transactions",
            params=params or None,
        )
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_transactions_by_payee(
        self,
        payee_id: str,
        plan_id: str,
        since_date: str | None = None,
        type: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> list[HybridTransaction]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if type:
            params["type"] = type
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/plans/{plan_id}/payees/{payee_id}/transactions",
            params=params or None,
        )
        return [HybridTransaction.model_validate(t) for t in data["data"]["transactions"]]

    async def create_transaction(self, transaction: dict, plan_id: str) -> Transaction:
        data = await self._post(
            f"/plans/{plan_id}/transactions",
            json={"transaction": transaction},
        )
        return Transaction.model_validate(data["data"]["transaction"])

    async def create_transactions(
        self, transactions: list[dict], plan_id: str
    ) -> list[Transaction]:
        data = await self._post(
            f"/plans/{plan_id}/transactions",
            json={"transactions": transactions},
        )
        return [
            Transaction.model_validate(t) for t in data["data"]["transactions"]
        ]

    async def update_transaction(
        self, transaction_id: str, transaction: dict, plan_id: str
    ) -> Transaction:
        data = await self._put(
            f"/plans/{plan_id}/transactions/{transaction_id}",
            json={"transaction": transaction},
        )
        return Transaction.model_validate(data["data"]["transaction"])

    async def update_transactions(
        self, transactions: list[dict], plan_id: str
    ) -> list[Transaction]:
        data = await self._patch(
            f"/plans/{plan_id}/transactions",
            json={"transactions": transactions},
        )
        return [
            Transaction.model_validate(t) for t in data["data"]["transactions"]
        ]

    async def delete_transaction(self, transaction_id: str, plan_id: str) -> Transaction:
        data = await self._delete(f"/plans/{plan_id}/transactions/{transaction_id}")
        return Transaction.model_validate(data["data"]["transaction"])

    async def import_transactions(self, plan_id: str) -> list[str]:
        data = await self._post(f"/plans/{plan_id}/transactions/import", json={})
        return data["data"]["transaction_ids"]

    # ── Categories ───────────────────────────────────────────

    async def get_categories(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[CategoryGroup], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/categories", params=params)
        groups = [CategoryGroup.model_validate(g) for g in data["data"]["category_groups"]]
        knowledge = data["data"]["server_knowledge"]
        return groups, knowledge

    async def create_category(self, category: dict, plan_id: str) -> Category:
        data = await self._post(
            f"/plans/{plan_id}/categories",
            json={"category": category},
        )
        return Category.model_validate(data["data"]["category"])

    async def get_category(self, category_id: str, plan_id: str) -> Category:
        data = await self._get(f"/plans/{plan_id}/categories/{category_id}")
        return Category.model_validate(data["data"]["category"])

    async def update_category(
        self, category_id: str, category: dict, plan_id: str
    ) -> Category:
        data = await self._patch(
            f"/plans/{plan_id}/categories/{category_id}",
            json={"category": category},
        )
        return Category.model_validate(data["data"]["category"])

    async def update_category_group(
        self, category_group_id: str, category_group: dict, plan_id: str
    ) -> CategoryGroup:
        data = await self._patch(
            f"/plans/{plan_id}/categories/groups/{category_group_id}",
            json={"category_group": category_group},
        )
        return CategoryGroup.model_validate(data["data"]["category_group"])

    async def create_category_group(self, category_group: dict, plan_id: str) -> CategoryGroup:
        data = await self._post(
            f"/plans/{plan_id}/category_groups",
            json={"category_group": category_group},
        )
        return CategoryGroup.model_validate(data["data"]["category_group"])

    async def get_category_for_month(
        self, month: str, category_id: str, plan_id: str
    ) -> Category:
        data = await self._get(
            f"/plans/{plan_id}/months/{month}/categories/{category_id}"
        )
        return Category.model_validate(data["data"]["category"])

    async def update_category_for_month(
        self, month: str, category_id: str, budgeted: int, plan_id: str
    ) -> Category:
        data = await self._patch(
            f"/plans/{plan_id}/months/{month}/categories/{category_id}",
            json={"category": {"budgeted": budgeted}},
        )
        return Category.model_validate(data["data"]["category"])

    # ── Payees ───────────────────────────────────────────────

    async def get_payees(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[Payee], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/payees", params=params)
        payees = [Payee.model_validate(p) for p in data["data"]["payees"]]
        knowledge = data["data"]["server_knowledge"]
        return payees, knowledge

    async def create_payee(self, payee: dict, plan_id: str) -> Payee:
        data = await self._post(
            f"/plans/{plan_id}/payees",
            json={"payee": payee},
        )
        return Payee.model_validate(data["data"]["payee"])

    async def get_payee(self, payee_id: str, plan_id: str) -> Payee:
        data = await self._get(f"/plans/{plan_id}/payees/{payee_id}")
        return Payee.model_validate(data["data"]["payee"])

    async def update_payee(self, payee_id: str, payee: dict, plan_id: str) -> Payee:
        data = await self._patch(
            f"/plans/{plan_id}/payees/{payee_id}",
            json={"payee": payee},
        )
        return Payee.model_validate(data["data"]["payee"])

    # ── Payee Locations ──────────────────────────────────────

    async def get_payee_locations(self, plan_id: str) -> list[PayeeLocation]:
        data = await self._get(f"/plans/{plan_id}/payee_locations")
        return [PayeeLocation.model_validate(pl) for pl in data["data"]["payee_locations"]]

    async def get_payee_location(
        self, payee_location_id: str, plan_id: str
    ) -> PayeeLocation:
        data = await self._get(f"/plans/{plan_id}/payee_locations/{payee_location_id}")
        return PayeeLocation.model_validate(data["data"]["payee_location"])

    async def get_payee_locations_by_payee(
        self, payee_id: str, plan_id: str
    ) -> list[PayeeLocation]:
        data = await self._get(f"/plans/{plan_id}/payees/{payee_id}/payee_locations")
        return [PayeeLocation.model_validate(pl) for pl in data["data"]["payee_locations"]]

    # ── Money Movements ──────────────────────────────────────

    async def get_money_movements(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[MoneyMovement], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/money_movements", params=params)
        movements = [MoneyMovement.model_validate(m) for m in data["data"]["money_movements"]]
        knowledge = data["data"]["server_knowledge"]
        return movements, knowledge

    async def get_money_movement_groups(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[MoneyMovementGroup], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/money_movement_groups", params=params)
        groups = [MoneyMovementGroup.model_validate(g) for g in data["data"]["money_movement_groups"]]
        knowledge = data["data"]["server_knowledge"]
        return groups, knowledge

    async def get_money_movement_groups_for_month(
        self, month: str, plan_id: str
    ) -> list[MoneyMovementGroup]:
        data = await self._get(f"/plans/{plan_id}/months/{month}/money_movement_groups")
        return [MoneyMovementGroup.model_validate(g) for g in data["data"]["money_movement_groups"]]

    async def get_money_movements_for_month(
        self, month: str, plan_id: str
    ) -> list[MoneyMovement]:
        data = await self._get(f"/plans/{plan_id}/months/{month}/money_movements")
        return [MoneyMovement.model_validate(m) for m in data["data"]["money_movements"]]

    # ── Months ───────────────────────────────────────────────

    async def get_months(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[MonthSummary], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/months", params=params)
        months = [MonthSummary.model_validate(m) for m in data["data"]["months"]]
        knowledge = data["data"]["server_knowledge"]
        return months, knowledge

    async def get_month(self, month: str, plan_id: str) -> MonthDetail:
        data = await self._get(f"/plans/{plan_id}/months/{month}")
        return MonthDetail.model_validate(data["data"]["month"])

    # ── Scheduled Transactions ───────────────────────────────

    async def create_scheduled_transaction(
        self, scheduled_transaction: dict, plan_id: str
    ) -> ScheduledTransaction:
        data = await self._post(
            f"/plans/{plan_id}/scheduled_transactions",
            json={"scheduled_transaction": scheduled_transaction},
        )
        return ScheduledTransaction.model_validate(data["data"]["scheduled_transaction"])

    async def update_scheduled_transaction(
        self,
        scheduled_transaction_id: str,
        scheduled_transaction: dict,
        plan_id: str,
    ) -> ScheduledTransaction:
        data = await self._put(
            f"/plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}",
            json={"scheduled_transaction": scheduled_transaction},
        )
        return ScheduledTransaction.model_validate(data["data"]["scheduled_transaction"])

    async def delete_scheduled_transaction(
        self, scheduled_transaction_id: str, plan_id: str
    ) -> ScheduledTransaction:
        data = await self._delete(
            f"/plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}"
        )
        return ScheduledTransaction.model_validate(data["data"]["scheduled_transaction"])

    async def get_scheduled_transactions(
        self, plan_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[ScheduledTransaction], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/plans/{plan_id}/scheduled_transactions", params=params)
        txns = [
            ScheduledTransaction.model_validate(t)
            for t in data["data"]["scheduled_transactions"]
        ]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_scheduled_transaction(
        self, transaction_id: str, plan_id: str
    ) -> ScheduledTransaction:
        data = await self._get(
            f"/plans/{plan_id}/scheduled_transactions/{transaction_id}"
        )
        return ScheduledTransaction.model_validate(data["data"]["scheduled_transaction"])

    async def close(self):
        await self._client.aclose()

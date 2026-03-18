import httpx
from typing import Any

from src.models import (
    Account,
    BudgetDetail,
    BudgetSummary,
    Category,
    CategoryGroup,
    MonthDetail,
    MonthSummary,
    Payee,
    ScheduledTransaction,
    Transaction,
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

    # ── Budgets ──────────────────────────────────────────────

    async def get_budgets(self) -> list[BudgetSummary]:
        data = await self._get("/budgets")
        return [BudgetSummary.model_validate(b) for b in data["data"]["budgets"]]

    async def get_budget(self, budget_id: str) -> BudgetDetail:
        data = await self._get(f"/budgets/{budget_id}")
        return BudgetDetail.model_validate(data["data"]["budget"])

    async def get_budget_settings(self, budget_id: str) -> dict:
        return await self._get(f"/budgets/{budget_id}/settings")

    # ── Accounts ─────────────────────────────────────────────

    async def get_accounts(
        self, budget_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[Account], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/budgets/{budget_id}/accounts", params=params)
        accounts = [Account.model_validate(a) for a in data["data"]["accounts"]]
        knowledge = data["data"]["server_knowledge"]
        return accounts, knowledge

    async def get_account(self, account_id: str, budget_id: str) -> Account:
        data = await self._get(f"/budgets/{budget_id}/accounts/{account_id}")
        return Account.model_validate(data["data"]["account"])

    # ── Transactions ─────────────────────────────────────────

    async def get_transactions(
        self,
        budget_id: str,
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
        data = await self._get(f"/budgets/{budget_id}/transactions", params=params or None)
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_transaction(self, transaction_id: str, budget_id: str) -> Transaction:
        data = await self._get(f"/budgets/{budget_id}/transactions/{transaction_id}")
        return Transaction.model_validate(data["data"]["transaction"])

    async def get_transactions_by_account(
        self,
        account_id: str,
        budget_id: str,
        since_date: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> tuple[list[Transaction], int]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/budgets/{budget_id}/accounts/{account_id}/transactions",
            params=params or None,
        )
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_transactions_by_category(
        self,
        category_id: str,
        budget_id: str,
        since_date: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> tuple[list[Transaction], int]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/budgets/{budget_id}/categories/{category_id}/transactions",
            params=params or None,
        )
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def get_transactions_by_payee(
        self,
        payee_id: str,
        budget_id: str,
        since_date: str | None = None,
        *,
        last_knowledge_of_server: int | None = None,
    ) -> tuple[list[Transaction], int]:
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        params = self._add_knowledge(params or None, last_knowledge_of_server) or {}
        data = await self._get(
            f"/budgets/{budget_id}/payees/{payee_id}/transactions",
            params=params or None,
        )
        txns = [Transaction.model_validate(t) for t in data["data"]["transactions"]]
        knowledge = data["data"]["server_knowledge"]
        return txns, knowledge

    async def create_transaction(self, transaction: dict, budget_id: str) -> Transaction:
        data = await self._post(
            f"/budgets/{budget_id}/transactions",
            json={"transaction": transaction},
        )
        return Transaction.model_validate(data["data"]["transaction"])

    async def create_transactions(
        self, transactions: list[dict], budget_id: str
    ) -> list[Transaction]:
        data = await self._post(
            f"/budgets/{budget_id}/transactions",
            json={"transactions": transactions},
        )
        return [
            Transaction.model_validate(t) for t in data["data"]["transactions"]
        ]

    async def update_transaction(
        self, transaction_id: str, transaction: dict, budget_id: str
    ) -> Transaction:
        data = await self._put(
            f"/budgets/{budget_id}/transactions/{transaction_id}",
            json={"transaction": transaction},
        )
        return Transaction.model_validate(data["data"]["transaction"])

    async def update_transactions(
        self, transactions: list[dict], budget_id: str
    ) -> list[Transaction]:
        data = await self._patch(
            f"/budgets/{budget_id}/transactions",
            json={"transactions": transactions},
        )
        return [
            Transaction.model_validate(t) for t in data["data"]["transactions"]
        ]

    async def delete_transaction(self, transaction_id: str, budget_id: str) -> Transaction:
        data = await self._delete(f"/budgets/{budget_id}/transactions/{transaction_id}")
        return Transaction.model_validate(data["data"]["transaction"])

    # ── Categories ───────────────────────────────────────────

    async def get_categories(
        self, budget_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[CategoryGroup], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/budgets/{budget_id}/categories", params=params)
        groups = [CategoryGroup.model_validate(g) for g in data["data"]["category_groups"]]
        knowledge = data["data"]["server_knowledge"]
        return groups, knowledge

    async def get_category(self, category_id: str, budget_id: str) -> Category:
        data = await self._get(f"/budgets/{budget_id}/categories/{category_id}")
        return Category.model_validate(data["data"]["category"])

    async def get_category_for_month(
        self, month: str, category_id: str, budget_id: str
    ) -> Category:
        data = await self._get(
            f"/budgets/{budget_id}/months/{month}/categories/{category_id}"
        )
        return Category.model_validate(data["data"]["category"])

    async def update_category_budget(
        self, month: str, category_id: str, budgeted: int, budget_id: str
    ) -> Category:
        data = await self._patch(
            f"/budgets/{budget_id}/months/{month}/categories/{category_id}",
            json={"category": {"budgeted": budgeted}},
        )
        return Category.model_validate(data["data"]["category"])

    # ── Payees ───────────────────────────────────────────────

    async def get_payees(
        self, budget_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[Payee], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/budgets/{budget_id}/payees", params=params)
        payees = [Payee.model_validate(p) for p in data["data"]["payees"]]
        knowledge = data["data"]["server_knowledge"]
        return payees, knowledge

    async def get_payee(self, payee_id: str, budget_id: str) -> Payee:
        data = await self._get(f"/budgets/{budget_id}/payees/{payee_id}")
        return Payee.model_validate(data["data"]["payee"])

    # ── Months ───────────────────────────────────────────────

    async def get_months(
        self, budget_id: str, *, last_knowledge_of_server: int | None = None
    ) -> tuple[list[MonthSummary], int]:
        params = self._add_knowledge(None, last_knowledge_of_server)
        data = await self._get(f"/budgets/{budget_id}/months", params=params)
        months = [MonthSummary.model_validate(m) for m in data["data"]["months"]]
        knowledge = data["data"]["server_knowledge"]
        return months, knowledge

    async def get_month(self, month: str, budget_id: str) -> MonthDetail:
        data = await self._get(f"/budgets/{budget_id}/months/{month}")
        return MonthDetail.model_validate(data["data"]["month"])

    # ── Scheduled Transactions ───────────────────────────────

    async def get_scheduled_transactions(self, budget_id: str) -> list[ScheduledTransaction]:
        data = await self._get(f"/budgets/{budget_id}/scheduled_transactions")
        return [
            ScheduledTransaction.model_validate(t)
            for t in data["data"]["scheduled_transactions"]
        ]

    async def get_scheduled_transaction(
        self, transaction_id: str, budget_id: str
    ) -> ScheduledTransaction:
        data = await self._get(
            f"/budgets/{budget_id}/scheduled_transactions/{transaction_id}"
        )
        return ScheduledTransaction.model_validate(data["data"]["scheduled_transaction"])

    async def close(self):
        await self._client.aclose()

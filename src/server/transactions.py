import json

from mcp.server.mcpserver import Context

from src.security import consent, diff
from src.server import _shared
from src.server._shared import dollars_to_milliunits, serialize, serialize_list


async def _transaction_preimage(transaction_id: str, plan_id: str) -> dict:
    """Read a transaction straight from the API, bypassing the cache.

    Bypassing the cache is not optional. A stale cached row would show the human
    a "before" that is not what YNAB actually holds, and the whole point of the
    consent prompt is that the before is true.
    """
    return (await _shared.client.get_transaction(transaction_id, plan_id)).model_dump()


def _prepare_subtransaction(sub: dict) -> dict:
    """Convert a subtransaction dict from dollars to milliunits and filter optional keys."""
    out: dict = {"amount": dollars_to_milliunits(sub["amount"])}
    for key in ("payee_id", "payee_name", "category_id", "memo"):
        if sub.get(key) is not None:
            out[key] = sub[key]
    return out


@_shared.mcp.tool()
@_shared.handle_errors
async def list_transactions(
    plan_id: str,
    since_date: str | None = None,
    type: str | None = None,
    exclude_fields: list[str] | None = None,
) -> str:
    """List transactions in a plan. Can filter by date and type.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
        type: Filter by 'uncategorized' or 'unapproved'
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_transactions(plan_id, since_date, type)
    return serialize_list(transactions, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_transaction(
    transaction_id: str,
    plan_id: str,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get a specific transaction by ID.

    Args:
        transaction_id: The transaction ID
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    txn = await _shared.cache.get_transaction(transaction_id, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_transactions_by_account(
    account_id: str,
    plan_id: str,
    since_date: str | None = None,
    type: str | None = None,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get transactions for a specific account, excluding pending transactions.

    Args:
        account_id: The account ID
        plan_id: The plan ID (use list_plans to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
        type: Filter by 'uncategorized' or 'unapproved'
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_transactions_by_account(
        account_id, plan_id, since_date, type
    )
    return serialize_list(transactions, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_transactions_by_category(
    category_id: str,
    plan_id: str,
    since_date: str | None = None,
    type: str | None = None,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get all transactions for a specific category, excluding pending transactions.

    Returns hybrid transactions which may represent regular transactions or subtransactions
    of split transactions. Each result includes a 'type' field ('transaction' or 'subtransaction')
    and 'parent_transaction_id' (set on subtransactions only).

    Args:
        category_id: The category ID
        plan_id: The plan ID (use list_plans to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
        type: Filter by 'uncategorized' or 'unapproved'
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_transactions_by_category(
        category_id, plan_id, since_date, type
    )
    return serialize_list(transactions, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_transactions_by_month(
    month: str,
    plan_id: str,
    since_date: str | None = None,
    type: str | None = None,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get all transactions for a specific plan month, excluding pending transactions.

    Args:
        month: Month in YYYY-MM-DD format (first of month) or 'current'
        plan_id: The plan ID (use list_plans to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
        type: Filter by 'uncategorized' or 'unapproved'
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_transactions_by_month(
        month, plan_id, since_date, type
    )
    return serialize_list(transactions, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def get_transactions_by_payee(
    payee_id: str,
    plan_id: str,
    since_date: str | None = None,
    type: str | None = None,
    exclude_fields: list[str] | None = None,
) -> str:
    """Get all transactions for a specific payee, excluding pending transactions.

    Returns hybrid transactions which may represent regular transactions or subtransactions
    of split transactions. Each result includes a 'type' field ('transaction' or 'subtransaction')
    and 'parent_transaction_id' (set on subtransactions only).

    Args:
        payee_id: The payee ID
        plan_id: The plan ID (use list_plans to find available IDs)
        since_date: Only return transactions on or after this date (YYYY-MM-DD)
        type: Filter by 'uncategorized' or 'unapproved'
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_transactions_by_payee(
        payee_id, plan_id, since_date, type
    )
    return serialize_list(transactions, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def search_transactions(
    plan_id: str,
    query: str,
    since_date: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    exclude_fields: list[str] | None = None,
) -> str:
    """Search transactions by text across payee, memo, and category fields.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        query: Text to search for (case-insensitive, matches payee, memo, and category)
        since_date: Only search transactions on or after this date (YYYY-MM-DD)
        amount_min: Minimum amount in dollars (e.g. -100.00). Filters by absolute value if both min and max are positive, otherwise by raw value.
        amount_max: Maximum amount in dollars (e.g. -10.00)
        exclude_fields: Optional list of field names to exclude from each transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transactions = await _shared.cache.get_transactions(plan_id, since_date)
    q = query.lower()

    matches = []
    for t in transactions:
        fields = [t.payee_name or "", t.memo or "", t.category_name or ""]
        if not any(q in f.lower() for f in fields):
            continue

        use_abs = (
            amount_min is not None
            and amount_max is not None
            and amount_min >= 0
            and amount_max >= 0
        )
        amount = abs(t.amount) if use_abs else t.amount
        if amount_min is not None and amount < dollars_to_milliunits(amount_min):
            continue
        if amount_max is not None and amount > dollars_to_milliunits(amount_max):
            continue

        matches.append(t)

    return serialize_list(matches, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def create_transaction(
    plan_id: str,
    account_id: str,
    date: str,
    amount: float,
    payee_id: str | None = None,
    payee_name: str | None = None,
    category_id: str | None = None,
    memo: str | None = None,
    cleared: str = "uncleared",
    approved: bool = False,
    flag_color: str | None = None,
    import_id: str | None = None,
    subtransactions: list[dict] | None = None,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a new transaction. Requires human confirmation.

    Future-dated transactions are not permitted (use scheduled transactions instead).

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        account_id: The account ID for this transaction
        date: Transaction date in YYYY-MM-DD format (must not be in the future)
        amount: Amount in dollars (negative for outflow, positive for inflow). e.g. -50.25 for spending $50.25
        payee_id: Payee ID (use list_payees to find available IDs). For account transfers, use the target account's transfer_payee_id.
        payee_name: Payee name. If payee_id is null, this resolves to an existing payee or creates a new one.
        category_id: Category ID. Use null with subtransactions to create a split. Credit Card Payment categories are ignored.
        memo: Memo/note (max 500 chars)
        cleared: 'cleared', 'uncleared', or 'reconciled'
        approved: Whether the transaction is approved
        flag_color: 'red', 'orange', 'yellow', 'green', 'blue', 'purple', or null
        import_id: Unique import identifier (max 36 chars). Used for matching against imported transactions.
        subtransactions: For splits, an array of dicts with keys: amount (dollars, required), payee_id, payee_name, category_id, memo
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transaction: dict = {
        "account_id": account_id,
        "date": date,
        "amount": dollars_to_milliunits(amount),
        "cleared": cleared,
        "approved": approved,
    }
    if payee_id:
        transaction["payee_id"] = payee_id
    if payee_name:
        transaction["payee_name"] = payee_name
    if category_id:
        transaction["category_id"] = category_id
    if flag_color:
        transaction["flag_color"] = flag_color
    if import_id:
        transaction["import_id"] = import_id
    if subtransactions:
        transaction["subtransactions"] = [
            _prepare_subtransaction(sub) for sub in subtransactions
        ]
    if memo:
        transaction["memo"] = memo

    fingerprint = await consent.confirm(
        ctx,
        action="Create transaction",
        plan_id=plan_id,
        payload=transaction,
        body=(
            "This transaction will be created:\n"
            f"  {diff.describe_transaction(transaction)}\n\n"
            "Exact fields sent to YNAB:\n"
            f"{diff.render_new_object(transaction)}"
        ),
    )
    consent.assert_unchanged(transaction, fingerprint)
    txn = await _shared.cache.create_transaction(transaction, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def create_transactions(
    plan_id: str,
    account_id: str,
    transactions: list[dict],
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create multiple transactions in a single API call. Requires human confirmation.

    Ideal for bulk imports.

    Future-dated transactions are not permitted. The response includes any duplicate_import_ids
    that were rejected because of an existing import_id on the same account.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        account_id: Default account ID for all transactions
        transactions: List of transaction dicts, each with:
            - date: Transaction date in YYYY-MM-DD format (required)
            - amount: Amount in dollars (required, negative for outflow, positive for inflow)
            - account_id: (optional) Override the default account ID
            - payee_id: (optional) Payee ID
            - payee_name: (optional) Payee name (resolves to existing or creates a new payee)
            - category_id: (optional) Category ID. Use null with subtransactions for splits.
            - memo: (optional) Memo (max 500 chars)
            - cleared: (optional) 'cleared', 'uncleared', or 'reconciled' (default: 'uncleared')
            - approved: (optional) Whether the transaction is approved (default: false)
            - flag_color: (optional) 'red', 'orange', 'yellow', 'green', 'blue', 'purple', or null
            - import_id: (optional) Unique import identifier (max 36 chars)
            - subtransactions: (optional) For splits, a list of subtransaction dicts with: amount, payee_id, payee_name, category_id, memo
        exclude_fields: Optional list of field names to exclude from each created transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    prepared = []
    for txn_input in transactions:
        txn: dict = {
            "account_id": txn_input.get("account_id", account_id),
            "date": txn_input["date"],
            "amount": dollars_to_milliunits(txn_input["amount"]),
            "cleared": txn_input.get("cleared", "uncleared"),
            "approved": txn_input.get("approved", False),
        }
        for key in ("payee_id", "payee_name", "category_id", "memo", "flag_color", "import_id"):
            if txn_input.get(key):
                txn[key] = txn_input[key]
        if txn_input.get("subtransactions"):
            txn["subtransactions"] = [
                _prepare_subtransaction(sub) for sub in txn_input["subtransactions"]
            ]
        prepared.append(txn)

    # Every row is itemised, never summarised as a count. "12 transactions" is
    # exactly the prompt a human waves through without having seen it. If that
    # makes the prompt long, the prompt is long: truncating here would be a
    # correctness bug, not a UX trade-off.
    listing = "\n".join(
        f"  {i:>3}. {diff.describe_transaction(t)}" for i, t in enumerate(prepared, 1)
    )
    fingerprint = await consent.confirm(
        ctx,
        action=f"Create {len(prepared)} transaction(s)",
        plan_id=plan_id,
        payload=prepared,
        body=f"All {len(prepared)} will be created:\n{listing}",
    )
    consent.assert_unchanged(prepared, fingerprint)
    txns = await _shared.cache.create_transactions(prepared, plan_id)
    return serialize_list(txns, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_transaction(
    plan_id: str,
    transaction_id: str,
    account_id: str | None = None,
    date: str | None = None,
    amount: float | None = None,
    payee_id: str | None = None,
    payee_name: str | None = None,
    category_id: str | None = None,
    memo: str | None = None,
    cleared: str | None = None,
    approved: bool | None = None,
    flag_color: str | None = None,
    subtransactions: list[dict] | None = None,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update an existing transaction. Requires human confirmation.

    Only provide the fields you want to change.

    Future-dated transactions are not permitted. Split transaction amounts and dates
    cannot be changed. If an existing transaction is a split, category_id cannot be
    changed and updating subtransactions is not supported.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        transaction_id: The transaction ID to update
        account_id: New account ID
        date: New date (YYYY-MM-DD, must not be in the future)
        amount: New amount in dollars (negative for outflow, positive for inflow)
        payee_id: New payee ID. For account transfers, use target account's transfer_payee_id.
        payee_name: New payee name (resolves to existing or creates a new payee)
        category_id: New category ID. Use null with subtransactions to create a split.
        memo: New memo (max 500 chars)
        cleared: 'cleared', 'uncleared', or 'reconciled'
        approved: Whether the transaction is approved
        flag_color: 'red', 'orange', 'yellow', 'green', 'blue', 'purple', or null
        subtransactions: For creating a new split, list of dicts with: amount, payee_id, payee_name, category_id, memo
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    transaction: dict = {}
    if account_id is not None:
        transaction["account_id"] = account_id
    if date is not None:
        transaction["date"] = date
    if amount is not None:
        transaction["amount"] = dollars_to_milliunits(amount)
    if payee_id is not None:
        transaction["payee_id"] = payee_id
    if payee_name is not None:
        transaction["payee_name"] = payee_name
    if category_id is not None:
        transaction["category_id"] = category_id
    if memo is not None:
        transaction["memo"] = memo
    if cleared is not None:
        transaction["cleared"] = cleared
    if approved is not None:
        transaction["approved"] = approved
    if flag_color is not None:
        transaction["flag_color"] = flag_color
    if subtransactions is not None:
        transaction["subtransactions"] = [
            _prepare_subtransaction(sub) for sub in subtransactions
        ]

    before = await _transaction_preimage(transaction_id, plan_id)
    fingerprint = await consent.confirm(
        ctx,
        action="Update transaction",
        plan_id=plan_id,
        subject=diff.describe_transaction(before),
        before=before,
        payload=transaction,
    )
    consent.assert_unchanged(transaction, fingerprint)
    txn = await _shared.cache.update_transaction(transaction_id, transaction, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def delete_transaction(
    transaction_id: str,
    plan_id: str,
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Delete a transaction. Requires human confirmation.

    Args:
        transaction_id: The transaction ID to delete
        plan_id: The plan ID (use list_plans to find available IDs)
        exclude_fields: Optional list of field names to exclude from the response.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    before = await _transaction_preimage(transaction_id, plan_id)
    target = {"transaction_id": transaction_id, "plan_id": plan_id}
    fingerprint = await consent.confirm(
        ctx,
        action="DELETE transaction",
        plan_id=plan_id,
        payload=target,
        body=(
            "This transaction will be permanently deleted:\n"
            f"  {diff.describe_transaction(before)}"
        ),
    )
    consent.assert_unchanged(target, fingerprint)
    txn = await _shared.cache.delete_transaction(transaction_id, plan_id)
    return serialize(txn, exclude_fields=exclude_fields)


@_shared.mcp.tool()
@_shared.handle_errors
async def import_transactions(plan_id: str, ctx: Context | None = None) -> str:
    """Import available transactions on all linked accounts. Requires human confirmation.

    Equivalent to clicking 'Import' on each account in the YNAB web app or tapping
    the 'New Transactions' banner in the mobile app. Returns the list of transaction
    IDs that were imported.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
    """
    # No diff is possible here: YNAB decides what gets imported, and the result
    # is not knowable in advance. Name the accounts that will be touched and say
    # so plainly rather than implying a preview that does not exist.
    accounts, _ = await _shared.client.get_accounts(plan_id)
    linked = [a for a in accounts if a.direct_import_linked and not a.closed and not a.deleted]
    if linked:
        affected = "\n".join(f"  - {a.name} ({a.type})" for a in linked)
    else:
        affected = "  (no accounts are currently linked for direct import)"
    target = {"action": "import_transactions", "plan_id": plan_id}
    fingerprint = await consent.confirm(
        ctx,
        action="Import transactions from linked accounts",
        plan_id=plan_id,
        payload=target,
        body=f"Accounts that may receive imported transactions:\n{affected}",
        note=(
            "YNAB decides which transactions are imported, so what this creates "
            "is NOT known in advance and cannot be previewed here."
        ),
    )
    consent.assert_unchanged(target, fingerprint)
    transaction_ids = await _shared.cache.import_transactions(plan_id)
    return json.dumps({"transaction_ids": transaction_ids}, indent=2)


@_shared.mcp.tool()
@_shared.handle_errors
async def update_transactions(
    plan_id: str,
    transactions: list[dict],
    exclude_fields: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Update multiple transactions in a single API call. Requires human confirmation.

    Each transaction must include either 'id' or 'import_id' for lookup (not both).
    Only provided fields are updated (sparse update). Ideal for bulk recategorization,
    bulk approval, bulk clearing, etc. Updating subtransactions on an existing split
    is not supported. Future-dated transactions are not permitted.

    Args:
        plan_id: The plan ID (use list_plans to find available IDs)
        transactions: List of transaction dicts. Each must include EITHER:
            - id: The transaction ID
            OR
            - import_id: The transaction's import_id (used for lookup, cannot be changed)
            And optionally any of:
            - account_id: New account ID
            - date: New date (YYYY-MM-DD)
            - amount: New amount in dollars (negative for outflow, positive for inflow)
            - payee_id: New payee ID
            - payee_name: New payee name
            - category_id: New category ID (use null with subtransactions to create a split)
            - memo: New memo (max 500 chars)
            - cleared: 'cleared', 'uncleared', or 'reconciled'
            - approved: Whether the transaction is approved
            - flag_color: 'red', 'orange', 'yellow', 'green', 'blue', 'purple', or null
            - subtransactions: For creating a new split, list of dicts with: amount, payee_id, payee_name, category_id, memo
        exclude_fields: Optional list of field names to exclude from each updated transaction.
            If omitted, the model's default exclude list is used (see FIELDS.md).
            Pass [] to return all fields. Pass a custom list to override the default.
    """
    prepared = []
    for txn_input in transactions:
        if "id" not in txn_input and "import_id" not in txn_input:
            return json.dumps({"error": "Each transaction must include either 'id' or 'import_id'"})
        txn: dict = {}
        if "id" in txn_input:
            txn["id"] = txn_input["id"]
        if "import_id" in txn_input:
            txn["import_id"] = txn_input["import_id"]
        if "account_id" in txn_input:
            txn["account_id"] = txn_input["account_id"]
        if "date" in txn_input:
            txn["date"] = txn_input["date"]
        if "amount" in txn_input:
            txn["amount"] = dollars_to_milliunits(txn_input["amount"])
        for key in ("payee_id", "payee_name", "category_id", "memo", "cleared", "approved", "flag_color"):
            if key in txn_input:
                txn[key] = txn_input[key]
        if txn_input.get("subtransactions"):
            txn["subtransactions"] = [
                _prepare_subtransaction(sub) for sub in txn_input["subtransactions"]
            ]
        prepared.append(txn)

    # Every row gets its own before/after. A row looked up by import_id has no
    # pre-image available — say so, rather than leaving a blank that reads as
    # "nothing changes".
    blocks = []
    for i, txn in enumerate(prepared, 1):
        changes = {k: v for k, v in txn.items() if k not in ("id", "import_id")}
        if "id" in txn:
            before = await _transaction_preimage(txn["id"], plan_id)
            header = f"  {i:>3}. {diff.describe_transaction(before)}"
        else:
            before = {}
            header = (
                f"  {i:>3}. (looked up by import_id {txn['import_id']}; "
                "no pre-image available)"
            )
        block = diff.render_change_block(
            diff.diff_fields(before, changes), indent="       "
        )
        blocks.append(header + "\n" + block)
    fingerprint = await consent.confirm(
        ctx,
        action=f"Update {len(prepared)} transaction(s)",
        plan_id=plan_id,
        payload=prepared,
        body="All {} will be updated:\n{}".format(
            len(prepared), "\n".join(blocks)
        ),
    )
    consent.assert_unchanged(prepared, fingerprint)
    txns = await _shared.cache.update_transactions(prepared, plan_id)
    return serialize_list(txns, exclude_fields=exclude_fields)

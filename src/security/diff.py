"""Rendering for consent prompts.

Everything a human is asked to approve is rendered here. The values that reach
these functions come from the YNAB API (the "before") and from the payload the
server is about to send (the "after") — never from prose the model wrote.

Amounts are milliunits throughout, matching the payload that goes on the wire,
so the number shown in the prompt is the number that gets sent.
"""

from typing import Any

# Fields carrying YNAB milliunits, rendered as currency rather than as integers.
MONEY_FIELDS: frozenset[str] = frozenset(
    {
        "amount",
        "balance",
        "cleared_balance",
        "uncleared_balance",
        "budgeted",
        "activity",
        "goal_target",
        "goal_overall_funded",
        "goal_overall_left",
        "goal_under_funded",
    }
)

_MISSING = object()


def format_money(milliunits: int | None) -> str:
    """Render milliunits as currency. 1000 milliunits = $1.00."""
    if milliunits is None:
        return "(none)"
    negative = milliunits < 0
    whole = abs(milliunits)
    # YNAB amounts are normally cent-aligned; show the third digit only when a
    # value actually uses it, rather than rounding it out of sight.
    text = f"{whole / 1000:,.3f}" if whole % 10 else f"{whole / 1000:,.2f}"
    return f"{'-' if negative else ''}${text}"


def format_value(field: str, value: Any) -> str:
    """Render one field value for display."""
    if value is _MISSING:
        return "(unchanged)"
    if value is None:
        return "(none)"
    if field in MONEY_FIELDS and isinstance(value, (int, float)) and not isinstance(value, bool):
        return format_money(int(value))
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value if value else '""'
    if isinstance(value, list):
        return f"[{len(value)} item{'s' if len(value) != 1 else ''}]"
    return str(value)


def describe_transaction(txn: dict) -> str:
    """One line describing a transaction, for itemising bulk operations."""
    parts = [
        str(txn.get("date") or "(no date)"),
        str(txn.get("payee_name") or txn.get("payee_id") or "(no payee)"),
        str(txn.get("category_name") or txn.get("category_id") or "(no category)"),
        format_money(txn.get("amount")),
    ]
    if txn.get("memo"):
        parts.append(f'memo "{txn["memo"]}"')
    parts.append(f"cleared={txn.get('cleared', 'uncleared')}")
    parts.append(f"approved={'yes' if txn.get('approved') else 'no'}")
    if txn.get("subtransactions"):
        parts.append(f"split into {len(txn['subtransactions'])}")
    return "  ".join(parts)


def describe_scheduled_transaction(txn: dict) -> str:
    """One line describing a scheduled transaction."""
    parts = [
        f"next {txn.get('date_next') or txn.get('date') or '(no date)'}",
        str(txn.get("frequency") or "(no frequency)"),
        str(txn.get("payee_name") or txn.get("payee_id") or "(no payee)"),
        str(txn.get("category_name") or txn.get("category_id") or "(no category)"),
        format_money(txn.get("amount")),
    ]
    if txn.get("memo"):
        parts.append(f'memo "{txn["memo"]}"')
    return "  ".join(parts)


def diff_fields(before: dict, after: dict) -> list[tuple[str, Any, Any]]:
    """Fields the payload would change, as (field, before, after).

    Only keys present in `after` are considered: a sparse update says nothing
    about the fields it omits, and listing them as unchanged would pad the
    prompt with noise a human then skims past.
    """
    changes: list[tuple[str, Any, Any]] = []
    for field, new in after.items():
        old = before.get(field, _MISSING)
        if old is _MISSING or old != new:
            changes.append((field, old, new))
    return changes


def render_change_block(changes: list[tuple[str, Any, Any]], indent: str = "  ") -> str:
    """Aligned `field: before -> after` lines."""
    if not changes:
        return f"{indent}(no fields would change)"
    width = max(len(field) for field, _, _ in changes)
    return "\n".join(
        f"{indent}{field:<{width}} : {format_value(field, old)} -> {format_value(field, new)}"
        for field, old, new in changes
    )


def render_new_object(payload: dict, indent: str = "  ") -> str:
    """Aligned `field: value` lines, for a create with no pre-image."""
    if not payload:
        return f"{indent}(empty)"
    width = max(len(field) for field in payload)
    return "\n".join(
        f"{indent}{field:<{width}} : {format_value(field, value)}"
        for field, value in payload.items()
    )

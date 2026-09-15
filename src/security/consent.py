"""Human confirmation for every mutating tool.

The security property this file exists to provide:

    the "before" shown to the human comes from the YNAB API, not from anything
    the model said, and the payload applied afterwards is byte-identical to the
    one that was shown.

Two things make that hold. First, a tool parameter annotated `Context` is
injected by the MCP SDK and does not appear in the tool's input schema, so the
model cannot supply, forge or suppress it; consent cannot be satisfied by
anything the model emits. Second, call sites fingerprint the resolved payload
before eliciting and assert the fingerprint afterwards, so a payload cannot be
re-resolved or recomputed between the prompt and the write.

Callers fetch the pre-image through `_shared.client`, which bypasses the cache.
That is not optional: a stale cache would show the human a false "before".
"""

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from src.security import diff


class ConsentDecision(BaseModel):
    """The elicitation schema. Primitive fields only, per the MCP spec."""

    confirm: bool = Field(
        description=(
            "True applies the change exactly as shown above. Anything else cancels "
            "it and nothing is sent to YNAB."
        )
    )


class ConsentUnavailable(Exception):
    """The client cannot ask a human, so the write must not happen."""


class ConsentDenied(Exception):
    """A human saw the change and said no."""


class ConsentViolation(Exception):
    """The payload changed between being shown and being sent. Never expected."""


class ReadOnlyMode(Exception):
    """Writes are disabled by configuration."""


_UNAVAILABLE_HELP = (
    "This write was blocked: the MCP client cannot obtain human confirmation. "
    "Every mutating YNAB tool requires a person to approve the exact change "
    "first, and this client does not support MCP elicitation "
    "(elicitation/create), so there is no way to ask. "
    "Fixes, in order of preference: use a client that supports elicitation; or "
    "make the change in the YNAB app directly; or run the server with "
    "YNAB_READ_ONLY=1 so the write tools stop being offered at all. "
    "The change was NOT applied."
)

_read_only = False


def set_read_only(value: bool) -> None:
    """Configure read-only mode for this process."""
    global _read_only
    _read_only = value


def is_read_only() -> bool:
    return _read_only


def payload_fingerprint(payload: Any) -> str:
    """A stable fingerprint of the exact payload that will be sent."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_unchanged(payload: Any, fingerprint: str) -> None:
    """Fail if the payload is not the one the human approved.

    Cheap, and it turns "apply exactly what was shown" from a convention into
    something a test can assert.
    """
    if payload_fingerprint(payload) != fingerprint:
        raise ConsentViolation(
            "The payload changed after it was approved; nothing was sent to YNAB. "
            "This is a bug in the server, not something you did."
        )


def _can_elicit(ctx: Any) -> bool:
    """Whether the connected client advertised elicitation support.

    Fails closed: if the capability cannot be established, the write is blocked
    rather than applied unconfirmed.
    """
    try:
        from mcp.types import ClientCapabilities, ElicitationCapability

        return bool(
            ctx.session.check_client_capability(
                ClientCapabilities(elicitation=ElicitationCapability())
            )
        )
    except Exception:
        return False


def render_prompt(
    *,
    action: str,
    plan_id: str | None,
    subject: str | None,
    before: dict | None,
    payload: Any,
    body: str | None,
    note: str | None,
) -> str:
    """Build the text a human is asked to approve."""
    lines = [f"CONFIRM: {action}"]
    if plan_id:
        lines.append(f"Plan: {plan_id}")
    lines.append("")

    if subject:
        lines.append("Current state, read from the YNAB API just now:")
        lines.append(f"  {subject}")
        lines.append("")

    if body is not None:
        lines.append(body)
    elif before is not None and isinstance(payload, dict):
        lines.append("This will change:")
        lines.append(diff.render_change_block(diff.diff_fields(before, payload)))
    elif isinstance(payload, dict):
        lines.append("This will be created:")
        lines.append(diff.render_new_object(payload))
    else:
        lines.append("Payload:")
        lines.append("  " + json.dumps(payload, indent=2).replace("\n", "\n  "))

    if note:
        lines.append("")
        lines.append(note)

    lines.append("")
    lines.append("Confirm to apply exactly this. Nothing else will be sent.")
    return "\n".join(lines)


async def confirm(
    ctx: Any,
    *,
    action: str,
    payload: Any,
    plan_id: str | None = None,
    subject: str | None = None,
    before: dict | None = None,
    body: str | None = None,
    note: str | None = None,
) -> str:
    """Ask a human to approve `payload`. Returns its fingerprint.

    Raises ReadOnlyMode, ConsentUnavailable or ConsentDenied rather than ever
    returning on a path where the write should not happen.
    """
    if _read_only:
        raise ReadOnlyMode(
            "This server is running in read-only mode (YNAB_READ_ONLY), so it "
            "cannot change anything in YNAB."
        )

    if ctx is None or not _can_elicit(ctx):
        raise ConsentUnavailable(_UNAVAILABLE_HELP)

    fingerprint = payload_fingerprint(payload)
    message = render_prompt(
        action=action,
        plan_id=plan_id,
        subject=subject,
        before=before,
        payload=payload,
        body=body,
        note=note,
    )

    try:
        result = await ctx.elicit(message=message, schema=ConsentDecision)
    except Exception as e:
        # No usable back-channel, a client that errored on the request, a
        # malformed response. Never degrade to applying the change.
        raise ConsentUnavailable(f"{_UNAVAILABLE_HELP} (client error: {e})") from e

    if getattr(result, "action", None) != "accept":
        raise ConsentDenied(
            f"Not confirmed ({getattr(result, 'action', 'unknown')}). "
            "Nothing was sent to YNAB."
        )
    data = getattr(result, "data", None)
    if data is None or not data.confirm:
        raise ConsentDenied("Declined by the user. Nothing was sent to YNAB.")

    return fingerprint

"""Billing-related lookups and actions used by the billing agent."""
from __future__ import annotations

from dataclasses import dataclass

from core import db

# In-memory ledger of refunds issued during this process's lifetime.
# In a real system this would be a write to the payments provider + DB.
_REFUNDS_ISSUED: list[dict] = []


@dataclass
class ToolResult:
    ok: bool
    message: str
    data: dict | None = None


def get_latest_invoice(customer_id: str) -> ToolResult:
    """Return the most recent invoice on file for a customer."""
    invoices = db.find_many("invoices", customer_id=customer_id)
    if not invoices:
        return ToolResult(
            ok=False,
            message=f"No invoices found for customer {customer_id}.",
        )
    latest = sorted(invoices, key=lambda inv: inv["date"], reverse=True)[0]
    return ToolResult(
        ok=True,
        message=(
            f"Latest invoice {latest['invoice_id']} dated {latest['date']}: "
            f"{latest['currency']} {latest['amount']} ({latest['status']}) - "
            f"{latest['description']}."
        ),
        data=latest,
    )


def process_refund(invoice_id: str, reason: str) -> ToolResult:
    """Issue a refund for a given invoice ID. Fails gracefully if the invoice doesn't exist."""
    invoice = db.find_one("invoices", invoice_id=invoice_id)
    if invoice is None:
        return ToolResult(
            ok=False,
            message=f"Invoice {invoice_id} was not found, so no refund could be issued.",
        )
    if invoice["status"] == "refunded":
        return ToolResult(
            ok=False,
            message=f"Invoice {invoice_id} has already been refunded previously.",
        )

    record = {
        "invoice_id": invoice_id,
        "customer_id": invoice["customer_id"],
        "amount": invoice["amount"],
        "currency": invoice["currency"],
        "reason": reason,
    }
    _REFUNDS_ISSUED.append(record)
    return ToolResult(
        ok=True,
        message=(
            f"Refund of {invoice['currency']} {invoice['amount']} issued for invoice "
            f"{invoice_id}. It should appear on the original payment method within "
            f"5-10 business days. Reason logged: {reason}."
        ),
        data=record,
    )


def list_refunds_issued() -> list[dict]:
    """Return all refunds issued so far (useful for tests/inspection)."""
    return list(_REFUNDS_ISSUED)

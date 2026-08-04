"""Order-status lookups used by the order-tracking agent."""
from __future__ import annotations

from core.billing import ToolResult
from core import db


def get_order_status(order_id: str) -> ToolResult:
    """Return shipping/status details for a given order ID."""
    order = db.find_one("orders", order_id=order_id)
    if order is None:
        return ToolResult(
            ok=False,
            message=f"No order found with ID {order_id}. Please double check the order number.",
        )

    if order["status"] == "delivered":
        detail = f"Order {order_id} ({order['item']}) was delivered on {order['eta']}."
    elif order["status"] == "delayed":
        detail = (
            f"Order {order_id} ({order['item']}) is delayed. New estimated delivery: "
            f"{order['eta']} via {order['carrier']}, tracking {order['tracking_number']}."
        )
    elif order["status"] == "shipped":
        detail = (
            f"Order {order_id} ({order['item']}) has shipped via {order['carrier']}, "
            f"tracking number {order['tracking_number']}. Estimated delivery: {order['eta']}."
        )
    else:  # processing
        detail = (
            f"Order {order_id} ({order['item']}) is still processing and hasn't shipped "
            f"yet. Estimated delivery: {order['eta']}."
        )

    return ToolResult(ok=True, message=detail, data=order)


def list_orders_for_customer(customer_id: str) -> list[dict]:
    """Return all orders belonging to a customer."""
    return db.find_many("orders", customer_id=customer_id)

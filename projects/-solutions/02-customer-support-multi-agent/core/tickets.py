"""Support-ticket creation for human hand-off / escalation."""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

_ticket_counter = itertools.count(1)
_TICKETS: list["Ticket"] = []


@dataclass
class Ticket:
    ticket_id: str
    customer_id: str | None
    category: str
    summary: str
    priority: str
    created_at: float = field(default_factory=time.time)
    status: str = "open"


def create_ticket(
    customer_id: str | None,
    category: str,
    summary: str,
    priority: str = "normal",
) -> Ticket:
    """Create a new support ticket and return it. `priority` is one of low/normal/high/urgent."""
    ticket_id = f"TCK-{next(_ticket_counter):05d}"
    ticket = Ticket(
        ticket_id=ticket_id,
        customer_id=customer_id,
        category=category,
        summary=summary,
        priority=priority,
    )
    _TICKETS.append(ticket)
    return ticket


def list_tickets() -> list[Ticket]:
    """Return every ticket created during this process's lifetime (mainly for tests/inspection)."""
    return list(_TICKETS)


def get_ticket(ticket_id: str) -> Ticket | None:
    for t in _TICKETS:
        if t.ticket_id == ticket_id:
            return t
    return None


def reset_tickets() -> None:
    """Clear all tickets (used by tests)."""
    _TICKETS.clear()

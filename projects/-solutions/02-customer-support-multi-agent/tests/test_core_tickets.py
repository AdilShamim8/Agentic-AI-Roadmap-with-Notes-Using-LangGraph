from core import tickets


def test_create_ticket_returns_unique_id():
    tickets.reset_tickets()
    t1 = tickets.create_ticket("CUST-1001", "billing", "Refund dispute", priority="high")
    t2 = tickets.create_ticket("CUST-1002", "technical", "Login broken", priority="urgent")
    assert t1.ticket_id != t2.ticket_id
    assert t1.status == "open"


def test_list_and_get_ticket():
    tickets.reset_tickets()
    created = tickets.create_ticket("CUST-1003", "order", "Package lost", priority="normal")
    assert tickets.get_ticket(created.ticket_id) is not None
    assert len(tickets.list_tickets()) == 1

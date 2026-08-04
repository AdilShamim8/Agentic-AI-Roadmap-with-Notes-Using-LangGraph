from core import orders


def test_get_order_status_shipped():
    result = orders.get_order_status("ORD-5001")
    assert result.ok is True
    assert "shipped" in result.message.lower()


def test_get_order_status_delayed_mentions_new_eta():
    result = orders.get_order_status("ORD-5004")
    assert result.ok is True
    assert "delayed" in result.message.lower()


def test_get_order_status_not_found():
    result = orders.get_order_status("ORD-0000")
    assert result.ok is False


def test_list_orders_for_customer():
    rows = orders.list_orders_for_customer("CUST-1001")
    assert len(rows) == 2

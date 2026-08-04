from core import billing


def test_get_latest_invoice_found():
    result = billing.get_latest_invoice("CUST-1001")
    assert result.ok is True
    assert result.data["invoice_id"] == "INV-9001"


def test_get_latest_invoice_not_found():
    result = billing.get_latest_invoice("CUST-9999")
    assert result.ok is False
    assert "No invoices" in result.message


def test_process_refund_success():
    result = billing.process_refund("INV-9002", reason="card declined but charged twice")
    assert result.ok is True
    assert "Refund" in result.message
    refunds = billing.list_refunds_issued()
    assert any(r["invoice_id"] == "INV-9002" for r in refunds)


def test_process_refund_missing_invoice():
    result = billing.process_refund("INV-0000", reason="test")
    assert result.ok is False

from core.intent import classify_intent, extract_ids
from core.sentiment import detect_sentiment, wants_human


def test_classify_billing():
    assert classify_intent("Why was I charged twice for my subscription?") == "billing"


def test_classify_order():
    assert classify_intent("Where is my package, order ORD-5001?") == "order"


def test_classify_technical():
    assert classify_intent("The app keeps crashing when I try to log in") == "technical"


def test_classify_general_fallback():
    assert classify_intent("What are your business hours?") == "general"


def test_extract_ids():
    ids = extract_ids("My order ORD-5002 and invoice inv-9002 both look wrong")
    assert ids["order_id"] == "ORD-5002"
    assert ids["invoice_id"] == "INV-9002"


def test_sentiment_neutral():
    assert detect_sentiment("Hi, can you help me check my order status?") == "neutral"


def test_sentiment_angry_keyword():
    assert detect_sentiment("This is absolutely unacceptable, I want a refund now") == "angry"


def test_sentiment_shouting():
    assert detect_sentiment("THIS IS THE THIRD TIME THIS HAS HAPPENED!!!") in ("angry", "frustrated")


def test_wants_human():
    assert wants_human("I want to speak to a real person please") is True
    assert wants_human("What's my order status?") is False

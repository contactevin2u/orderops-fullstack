import json
from typing import Any, Dict

import pytest

import app.parsing.parse as parse


def _mock_response(payload: Dict[str, Any]):
    class Msg:
        def __init__(self, content: str):
            self.content = content

    class Choice:
        def __init__(self, content: str):
            self.message = Msg(content)

    class Usage:
        def __init__(self):
            self.total_tokens = 42

    class Resp:
        def __init__(self, content: str):
            self.choices = [Choice(content)]
            self.usage = Usage()

    return Resp(json.dumps(payload))


def test_caching_and_classification(monkeypatch):
    sample = {
        "order_id_hint": "2024-AB123",
        "customer_name": "Mr Lim",
        "phone": "012-3456789",
        "event_type": "RETURN",
        "appointment_date": None,
        "appointment_time": None,
        "items": [],
        "amounts": {
            "subtotal": None,
            "delivery_fee": None,
            "penalty_amount": None,
            "buyback_amount": None,
            "total": None,
        },
        "notes": None,
    }

    calls: list[int] = []

    def fake_create(*args, **kwargs):
        calls.append(1)
        return _mock_response(sample)

    monkeypatch.setattr(
        parse.client.chat.completions, "create", fake_create
    )

    text = "Hi, return bed tomorrow 3pm, order 2024-AB123, Mr Lim 012-3456789."
    parse._CACHE.clear()
    result1 = parse.parse_order(text)
    result2 = parse.parse_order(text)

    assert result1 == result2
    assert len(calls) == 1  # cached second call
    assert result1["classification"] == "RETURNED"

import sys, json
from pathlib import Path

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services import parser  # noqa: E402
from app.core.config import settings  # noqa: E402


class FullClient:
    class Responses:
        def create(self, **kwargs):
            data = {
                "customer": {"name": "Ali"},
                "order": {
                    "type": "OUTRIGHT",
                    "items": [
                        {
                            "name": "Chair",
                            "qty": 1,
                            "unit_price": 100,
                            "line_total": 100,
                            "item_type": "OUTRIGHT",
                        }
                    ],
                    "charges": {"delivery_fee": 10},
                    "totals": {},
                },
            }
            content = json.dumps(data)

            class Resp:
                def __init__(self, content):
                    self.output_text = content

            return Resp(content)

    def __init__(self):
        self.responses = FullClient.Responses()


class FailingClient:
    class Responses:
        def create(self, **kwargs):
            raise RuntimeError("fail")

    def __init__(self):
        self.responses = FailingClient.Responses()


def test_heuristic_only_on_failure(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_PARSE_REAL", True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test")

    calls = {"count": 0}

    def fake_heuristic(text):
        calls["count"] += 1
        return {"order": {"items": [{"name": "heur"}], "charges": {"delivery_fee": 1}}}

    monkeypatch.setattr(parser, "_heuristic_fallback", fake_heuristic)

    # Success path: heuristics not called
    monkeypatch.setattr(parser, "_openai_client", lambda: FullClient())
    parser.parse_whatsapp_text("item RM100")
    assert calls["count"] == 0

    # Failure path: heuristics called once
    monkeypatch.setattr(parser, "_openai_client", lambda: FailingClient())
    parser.parse_whatsapp_text("item RM100")
    assert calls["count"] == 1

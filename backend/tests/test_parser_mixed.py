import sys, json
from pathlib import Path

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.parser import parse_whatsapp_text  # noqa: E402
from app.routers.parse import _post_normalize  # noqa: E402
from app.core.config import settings  # noqa: E402

class DummyClient:
    class Chat:
        class Completions:
            def create(self, **kwargs):
                data = {
                    "customer": {"name": "Ali"},
                    "order": {
                        "type": "MIXED",
                        "items": [
                            {"name": "Wheelchair", "qty": 1, "unit_price": 500, "line_total": 500, "item_type": "OUTRIGHT"},
                            {"name": "Hospital Bed", "qty": 1, "monthly_amount": 200, "item_type": "RENTAL"},
                        ],
                        "charges": {},
                        "plan": {"months": 1, "monthly_amount": 200},
                        "totals": {},
                    },
                }
                content = json.dumps(data)
                class Message:
                    def __init__(self, content):
                        self.content = content
                class Choice:
                    def __init__(self, content):
                        self.message = Message(content)
                class Resp:
                    def __init__(self, content):
                        self.choices = [Choice(content)]
                return Resp(content)

        def __init__(self):
            self.completions = DummyClient.Chat.Completions()

    def __init__(self):
        self.chat = DummyClient.Chat()

def test_parse_mixed_items(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_PARSE_REAL", True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.services.parser._openai_client", lambda: DummyClient())

    text = "WC2009\nBeli Wheelchair RM500\nSewa Bed RM200"
    data = parse_whatsapp_text(text)
    norm = _post_normalize(data, text)

    assert norm["order"]["type"] == "MIXED"
    assert norm["order"]["items"][0]["item_type"] == "OUTRIGHT"
    assert norm["order"]["items"][1]["item_type"] == "RENTAL"
    assert norm["order"]["plan"]["plan_type"] == "RENTAL"

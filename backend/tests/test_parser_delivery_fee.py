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
                        "type": "OUTRIGHT",
                        "items": [],
                        "charges": {},
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

def test_parse_item_and_delivery_fee(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.services.parser._openai_client", lambda: DummyClient())

    text = "tilam canvas RM199\nPenghantaran RM20"
    data = parse_whatsapp_text(text)
    norm = _post_normalize(data, text)

    assert norm["order"]["items"]
    assert norm["order"]["items"][0]["name"].lower() == "tilam canvas"
    assert float(norm["order"]["items"][0]["line_total"]) == 199
    assert float(norm["order"]["charges"]["delivery_fee"]) == 20


def test_parse_delivery_fee_foc(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.services.parser._openai_client", lambda: DummyClient())

    text = "Auto travel steel wheelchair RM2200\nDelivery FOC"
    data = parse_whatsapp_text(text)
    norm = _post_normalize(data, text)

    assert float(norm["order"]["charges"].get("delivery_fee", 0)) == 0
    assert float(norm["order"]["totals"]["total"]) == 2200

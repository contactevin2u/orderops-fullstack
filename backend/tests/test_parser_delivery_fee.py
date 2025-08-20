import sys, json
from pathlib import Path

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.parser import parse_whatsapp_text  # noqa: E402
from app.routers.parse import _post_normalize  # noqa: E402
from app.core.config import settings  # noqa: E402


class DummyClient:
    class Responses:
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

            class Resp:
                def __init__(self, content):
                    self.output_text = content

            return Resp(content)

    def __init__(self):
        self.responses = DummyClient.Responses()

def test_parse_item_and_delivery_fee(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_PARSE_REAL", True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.services.parser._openai_client", lambda: DummyClient())

    text = "tilam canvas RM199\nPenghantaran RM20"
    data = parse_whatsapp_text(text)
    norm = _post_normalize(data, text)

    assert norm["order"]["items"]
    assert norm["order"]["items"][0]["name"].lower() == "tilam canvas"
    assert float(norm["order"]["items"][0]["line_total"]) == 199
    assert float(norm["order"]["charges"]["delivery_fee"]) == 20

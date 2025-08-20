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

def test_parse_mixed_items(monkeypatch):
    monkeypatch.setattr(settings, "FEATURE_PARSE_REAL", True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.services.parser._openai_client", lambda: DummyClient())

    text = (
        "WC2009\n"
        "Beli Wheelchair RM500\n"
        "Sewa Bed RM200\n"
        "Ventilator RM1000 x5"
    )
    data = parse_whatsapp_text(text)
    norm = _post_normalize(data, text)

    assert norm["order"]["type"] == "MIXED"
    assert norm["order"]["items"][0]["item_type"] == "OUTRIGHT"
    assert norm["order"]["items"][1]["item_type"] == "RENTAL"
    assert norm["order"]["items"][2]["item_type"] == "INSTALLMENT"
    assert norm["order"]["plan"]["plan_type"] == "INSTALLMENT"
    assert float(norm["order"]["plan"]["monthly_amount"]) == 1000
    assert norm["order"]["plan"]["months"] == 5

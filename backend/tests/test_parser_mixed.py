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
                text = kwargs["messages"][-1]["content"]
                data = {
                    "customer": {"name": "Ali"},
                    "order": {
                        "type": "MIXED",
                        "code": "WC2009",
                        "items": [
                            {
                                "name": "Beli Wheelchair",
                                "qty": 1,
                                "unit_price": 500,
                                "line_total": 500,
                                "item_type": "OUTRIGHT",
                            },
                            {
                                "name": "Sewa Bed",
                                "qty": 1,
                                "unit_price": 200,
                                "line_total": 200,
                                "item_type": "RENTAL",
                            },
                            {
                                "name": "Ventilator",
                                "qty": 1,
                                "unit_price": 1000,
                                "line_total": 1000,
                                "item_type": "INSTALLMENT",
                                "monthly_amount": 1000,
                            },
                        ],
                        "plan": {
                            "plan_type": "INSTALLMENT",
                            "months": 5,
                            "monthly_amount": 1000,
                        },
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

def test_parse_mixed_items(monkeypatch):
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

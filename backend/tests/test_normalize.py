import sys
from pathlib import Path
from decimal import Decimal

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.normalize import to_decimal, ensure_dict, ensure_list  # noqa: E402


def test_to_decimal_handles_various_inputs():
    assert to_decimal(None) == Decimal("0.00")
    assert to_decimal("3.456") == Decimal("3.46")
    assert to_decimal("not a number") == Decimal("0.00")
    assert to_decimal(Decimal("1.235")) == Decimal("1.24")


def test_ensure_dict_and_list_defaults():
    assert ensure_dict(None) == {}
    assert ensure_dict({"a": 1}) == {"a": 1}
    assert ensure_list(None) == []
    assert ensure_list("foo") == []
    assert ensure_list([1, 2]) == [1, 2]

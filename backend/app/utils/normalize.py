from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any, Dict, List

DECIMAL_ZERO = Decimal("0.00")


def to_decimal(value: Any, default: Decimal = DECIMAL_ZERO) -> Decimal:
    """Safely coerce ``value`` into a :class:`~decimal.Decimal` rounded to 2dp.

    ``None`` or invalid inputs return ``default`` (0.00 by default).
    """
    if value is None:
        return default
    if isinstance(value, Decimal):
        try:
            return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return default
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return default


def ensure_dict(x: Any) -> Dict[str, Any]:
    """Return ``x`` if it's a ``dict`` else an empty dict."""
    return x if isinstance(x, dict) else {}


def ensure_list(x: Any) -> List[Any]:
    """Return ``x`` if it's a ``list`` else an empty list."""
    return x if isinstance(x, list) else []

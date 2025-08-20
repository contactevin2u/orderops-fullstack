from __future__ import annotations

from datetime import date, datetime
import re
from typing import Optional


def parse_relaxed_date(text: str) -> Optional[date]:
    """Parse loose date strings.

    Accepts inputs like ``"19/8"``, ``"19-08"`` (assuming current year),
    ``"19/08/2025"`` (two or four digit years) and ISO formats such as
    ``"2025-08-19"``. Returns ``None`` when parsing fails.
    """
    if not text:
        return None

    s = text.strip().lower()

    # Try ISO format first
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        pass

    # Look for dd[/|-]mm[/|-]yyyy? pattern anywhere in the string
    m = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_part = m.group(3)
        if year_part is None:
            year = datetime.utcnow().year
        else:
            year = int(year_part)
            if year < 100:
                year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None

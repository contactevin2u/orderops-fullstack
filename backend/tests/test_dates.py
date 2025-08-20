import sys
from pathlib import Path
from datetime import date

# Ensure backend package is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.dates import parse_relaxed_date  # noqa: E402


def test_parse_dd_slash_mm_current_year():
    d = parse_relaxed_date("19/8")
    assert d == date(date.today().year, 8, 19)


def test_parse_dd_dash_mm_current_year():
    d = parse_relaxed_date("19-08")
    assert d == date(date.today().year, 8, 19)


def test_parse_iso_format():
    d = parse_relaxed_date("2025-08-19")
    assert d == date(2025, 8, 19)


def test_parse_invalid_returns_none():
    assert parse_relaxed_date("not a date") is None

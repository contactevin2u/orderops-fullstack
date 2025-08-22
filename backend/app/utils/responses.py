"""Response helpers for API endpoints."""
from typing import Any


def envelope(data: Any | None = None, *, ok: bool = True, error: str | None = None) -> dict:
    """Return a standardized response envelope."""
    resp = {"ok": ok and error is None, "data": data}
    if error:
        resp["error"] = error
    return resp

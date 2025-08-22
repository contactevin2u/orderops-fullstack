from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict

import os
from openai import OpenAI
from prometheus_client import Counter, Histogram
from jsonschema import validate

try:  # optional JSON repair utility
    from json_repair import repair_json
except Exception:  # pragma: no cover
    def repair_json(data: str) -> str:  # type: ignore
        return data

try:  # optional product alias support
    from rapidfuzz.process import extractOne  # type: ignore
except Exception:  # pragma: no cover
    extractOne = None  # type: ignore

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.txt"
SCHEMA_PATH = Path(__file__).parent / "schema" / "order_intake.schema.json"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "test"))

# simple in-memory cache for idempotency
_CACHE: Dict[str, Dict[str, Any]] = {}

PARSE_LATENCY = Histogram(
    "order_parse_latency_seconds",
    "Latency for order parsing",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
PARSE_SUCCESS = Counter("order_parse_success_total", "Number of successful parses")
PARSE_FAIL = Counter("order_parse_fail_total", "Number of failed parses")
PARSE_RETRY = Counter("order_parse_retry_total", "Number of parse retries")
PARSE_TOKENS = Counter("order_parse_tokens_total", "Tokens used during parsing")

CLASSIFICATION_MAP = {
    "RETURN": "RETURNED",
    "COLLECT": "RETURNED",
    "INSTALMENT_CANCEL": "CANCELLED",
    "BUYBACK": "CANCELLED",
}


def _alias_items(items: list[Dict[str, Any]]) -> None:
    """Map item names to SKU using RapidFuzz when available."""
    if not extractOne:
        return
    # Example alias mapping; in production replace with real catalog
    aliases = {
        "bed": "BEDSKU",
        "sofa": "SOFASKU",
    }
    names = list(aliases.keys())
    for item in items:
        name = item.get("name")
        if name and not item.get("sku"):
            match = extractOne(name, names, score_cutoff=80)
            if match:
                item["sku"] = aliases[match[0]]


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply domain specific normalization."""
    event = data.get("event_type")
    data["classification"] = CLASSIFICATION_MAP.get(event, "NONE")
    _alias_items(data.get("items", []))
    return data


def parse_order(text: str) -> Dict[str, Any]:
    """Parse an incoming order message into structured data.

    Args:
        text: Raw user message.

    Returns:
        Parsed order dictionary adhering to the domain schema.
    """
    msg_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if msg_hash in _CACHE:
        return _CACHE[msg_hash]

    schema = json.loads(SCHEMA_PATH.read_text())
    sys_prompt = PROMPT_PATH.read_text()

    for attempt in range(3):
        start = time.time()
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_schema", "json_schema": schema},
            )
            latency = time.time() - start
            PARSE_LATENCY.observe(latency)
            PARSE_TOKENS.inc(getattr(getattr(resp, "usage", None), "total_tokens", 0))

            content = resp.choices[0].message.content
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = json.loads(repair_json(content))
            validate(instance=data, schema=schema)
            normalized = _normalize(data)
            _CACHE[msg_hash] = normalized
            PARSE_SUCCESS.inc()
            return normalized
        except Exception:  # pragma: no cover - errors handled via counters
            latency = time.time() - start
            PARSE_LATENCY.observe(latency)
            logging.exception("parse attempt failed")
            PARSE_RETRY.inc()
            time.sleep(0.25 * (2 ** attempt))
    PARSE_FAIL.inc()
    raise RuntimeError("parse failed after retries")


__all__ = ["parse_order"]

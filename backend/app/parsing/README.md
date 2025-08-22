# OpenAI Order Parsing

This module provides a thin wrapper around OpenAI's structured output API to
extract structured order intents from free-form messages.

## Usage

```python
from app.parsing.parse import parse_order
result = parse_order("Hi, return bed tomorrow 3pm, order 2024-AB123, Mr Lim 012-3456789.")
```

## Development

* Prompts live in `prompts/system.txt`.
* JSON schema lives in `schema/order_intake.schema.json`.
* Update either file and commit the changes. Roll back by reverting the commit.

## Evaluation

The evaluation harness runs the parser against a golden set and reports field
level metrics.

```bash
python -m app.parsing.eval
```

## Telemetry

Prometheus metrics are exposed when the module is imported:

* `order_parse_latency_seconds`
* `order_parse_success_total`
* `order_parse_fail_total`
* `order_parse_retry_total`
* `order_parse_tokens_total`

## Rollback

To roll back to a previous parser version, revert the git commit that changed
this module, prompts, or schema and redeploy the backend.

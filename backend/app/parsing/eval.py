from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Dict, List

from .parse import parse_order

DATA_PATH = Path(__file__).parent / "data" / "golden_set.jsonl"


def load_dataset() -> List[Dict[str, object]]:
    examples: List[Dict[str, object]] = []
    with DATA_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(json.loads(line))
    return examples


def evaluate() -> Dict[str, object]:
    examples = load_dataset()
    metrics = {
        "event_type": {"tp": 0, "fp": 0, "fn": 0},
        "customer_name": {"tp": 0, "fp": 0, "fn": 0},
        "phone": {"tp": 0, "fp": 0, "fn": 0},
    }
    amount_errors: List[float] = []
    for ex in examples:
        parsed = parse_order(ex["text"])  # type: ignore[arg-type]
        expected = ex["expected"]
        for field in metrics.keys():
            p = parsed.get(field)
            e = expected.get(field)  # type: ignore[index]
            if p == e and p not in (None, ""):
                metrics[field]["tp"] += 1
            if p and p != e:
                metrics[field]["fp"] += 1
            if e and p != e:
                metrics[field]["fn"] += 1
        pe = parsed.get("amounts", {}).get("total")
        ee = expected.get("amounts", {}).get("total")  # type: ignore[index]
        if pe is not None and ee is not None:
            amount_errors.append(abs(pe - ee) / max(ee, 1))
    report: Dict[str, object] = {}
    for field, m in metrics.items():
        precision = m["tp"] / (m["tp"] + m["fp"]) if (m["tp"] + m["fp"]) else 0.0
        recall = m["tp"] / (m["tp"] + m["fn"]) if (m["tp"] + m["fn"]) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        report[field] = {"precision": precision, "recall": recall, "f1": f1}
    report["amount_total_mean_abs_pct_error"] = mean(amount_errors) if amount_errors else None
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    evaluate()

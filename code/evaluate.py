"""Per-field exact-match accuracy against dataset/sample_requests.csv.

Runs the full pipeline (load → OCR → messages → forecast → decide) on the 25
sample requests, then compares each output field to the gold labels.

Usage:
    python code/evaluate.py

Prints a table: field name, N correct / 25, accuracy %.
amount_safe_to_pay uses a ±1 % numeric tolerance.
All other fields: strip + lower-case exact match.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

# Make sibling modules importable when running as a script
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from load_inputs import load_all, DATASET
from forecast import build_forecast
from decide import decide_all
from ocr import run as run_ocr
from parse_messages import run as run_messages

SAMPLE = DATASET / "sample_requests.csv"

FIELDS = [
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

AMOUNT_TOL = 0.01  # ±1 %


def _load_gold() -> dict[str, dict]:
    gold: dict[str, dict] = {}
    with SAMPLE.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            gold[row["request_id"]] = row
    return gold


def _match_amount(gold: str, pred: str) -> bool:
    try:
        g, p = float(gold.strip()), float(pred.strip())
    except ValueError:
        return gold.strip().lower() == pred.strip().lower()
    if g == 0 and p == 0:
        return True
    if g == 0:
        return abs(p) < 1e-6
    return abs(g - p) / abs(g) <= AMOUNT_TOL


def _match(field: str, gold: str, pred: str) -> bool:
    if field == "amount_safe_to_pay":
        return _match_amount(gold, pred)
    return gold.strip().lower() == pred.strip().lower()


def _run_pipeline() -> dict[str, dict]:
    """Return predictions keyed by request_id for sample requests."""
    print("Loading inputs from sample_requests.csv ...", file=sys.stderr)
    inputs = load_all(verbose=False, requests_path=SAMPLE)

    print("Running OCR on images ...", file=sys.stderr)
    ocr_results = run_ocr(inputs.images, inputs.evidence_complete)

    print("Parsing messages ...", file=sys.stderr)
    msg_results = run_messages(inputs.messages)

    print("Building forecasts ...", file=sys.stderr)
    forecasts = build_forecast(inputs, ocr_results, msg_results)

    print("Making decisions ...", file=sys.stderr)
    rows = decide_all(inputs, forecasts)

    return {r["request_id"]: r for r in rows}


def evaluate() -> None:
    gold = _load_gold()
    pred = _run_pipeline()

    sample_ids = sorted(gold.keys())
    missing = [rid for rid in sample_ids if rid not in pred]
    if missing:
        print(f"WARNING: {len(missing)} sample IDs not in predictions: {missing}", file=sys.stderr)

    total = len(sample_ids)
    counts: dict[str, int] = {f: 0 for f in FIELDS}

    for rid in sample_ids:
        if rid not in pred:
            continue
        g, p = gold[rid], pred[rid]
        for field in FIELDS:
            if _match(field, g.get(field, ""), str(p.get(field, ""))):
                counts[field] += 1

    col_w = max(len(f) for f in FIELDS) + 2
    print(f"\n{'Field':<{col_w}}  {'Correct':>9}  {'Accuracy':>9}")
    print("-" * (col_w + 24))
    total_correct = 0
    for field in FIELDS:
        c = counts[field]
        total_correct += c
        pct = 100.0 * c / total if total else 0.0
        marker = " *" if field == "amount_safe_to_pay" else ""
        print(f"{field:<{col_w}}  {c:>4} / {total:<3}  {pct:>8.1f}%{marker}")
    print("-" * (col_w + 24))
    overall_pct = 100.0 * total_correct / (total * len(FIELDS)) if total else 0.0
    print(f"{'Overall (all fields)':<{col_w}}  {total_correct:>4} / {total * len(FIELDS):<3}  {overall_pct:>8.1f}%")
    print(f"\n* amount_safe_to_pay uses ±{int(AMOUNT_TOL * 100)}% numeric tolerance\n")


if __name__ == "__main__":
    evaluate()

"""Entry point: run all pipeline stages and write output.csv."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from load_inputs import load_all
from ocr import run as run_ocr
from parse_messages import run as run_messages
from forecast import build_forecast
from decide import decide_all

OUTPUT_COLS = [
    "request_id", "amount_safe_to_pay", "affordability_status",
    "recommended_payment_method", "payment_plan",
    "earliest_date_for_full_payment", "spending_changes_needed",
    "decision_explanation",
]

ROOT = Path(__file__).parent.parent


def main() -> None:
    print("Stage 1: loading inputs...")
    inputs = load_all(verbose=True)

    print("\nStage 1b: OCR images...")
    ocr_results = run_ocr(inputs.images, inputs.evidence_complete)
    print(f"  {sum(r is not None for r in ocr_results.values())}/{len(ocr_results)} images parsed")

    print("\nStage 1c: parsing messages...")
    message_results = run_messages(inputs.messages)
    print(f"  {sum(r is not None for r in message_results.values())}/{len(message_results)} messages parsed")

    print("\nStage 2: building forecasts...")
    forecasts = build_forecast(inputs, ocr_results, message_results)
    print(f"  {len(forecasts)} forecasts built")

    print("\nStage 3: deciding...")
    rows = decide_all(inputs, forecasts)
    print(f"  {len(rows)} decisions made")

    print("\nStage 4: writing output.csv...")
    df = pd.DataFrame(rows, columns=OUTPUT_COLS)
    out_path = ROOT / "output.csv"
    df.to_csv(out_path, index=False)
    print(f"  written to {out_path}")

    counts = df["affordability_status"].value_counts().to_dict()
    print(f"  status counts: {counts}")


if __name__ == "__main__":
    main()

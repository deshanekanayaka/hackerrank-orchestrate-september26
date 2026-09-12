"""Extract monetary amounts from images using Claude Haiku vision."""
from __future__ import annotations
import base64
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cache import get as cache_get, put as cache_put
from model_client import CLIENT, MODEL, call_with_retry
from prompts import IMAGE_PROMPT, ImageResult, strip_fences

_DATASET = Path(__file__).parent.parent / "dataset"


def _call(img_path: Path) -> ImageResult:
    data = base64.standard_b64encode(img_path.read_bytes()).decode()
    msg = CLIENT.messages.create(
        model=MODEL,
        max_tokens=256,
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
                {"type": "text", "text": IMAGE_PROMPT},
            ],
        }],
    )
    return ImageResult(**json.loads(strip_fences(msg.content[0].text)))


def run(
    images_df,
    evidence_complete: dict[str, bool],
) -> dict[str, ImageResult | None]:
    """OCR all images. Sets evidence_complete[user_id]=False on unrecoverable failure."""
    results: dict[str, ImageResult | None] = {}
    for _, row in images_df.iterrows():
        image_id = row["image_id"]
        user_id = row["user_id"]
        img_path = _DATASET / "media" / "images" / f"{image_id}.png"

        if not img_path.exists():
            results[image_id] = None
            evidence_complete[user_id] = False
            continue

        file_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()
        cache_key = f"ocr:{image_id}:{file_hash}"
        cached = cache_get(cache_key)
        if cached is not None:
            results[image_id] = ImageResult(**cached)
            continue

        result = call_with_retry(lambda p=img_path: _call(p), image_id)
        if result is None:
            print(f"  [warn] ocr {image_id} — marking user {user_id} incomplete", file=sys.stderr)
            evidence_complete[user_id] = False
        else:
            cache_put(cache_key, {"amount": result.amount, "currency": result.currency})
        results[image_id] = result

    return results


if __name__ == "__main__":
    import pandas as pd

    images = pd.read_csv(_DATASET / "images.csv", dtype=str, keep_default_na=False)
    sample = images.head(2)
    ec: dict[str, bool] = {uid: True for uid in sample["user_id"].unique()}

    print(f"Running OCR on {len(sample)} images...")
    results = run(sample, ec)

    for iid, r in results.items():
        print(f"  {iid}: {r}")
    print(f"evidence_complete: {ec}")

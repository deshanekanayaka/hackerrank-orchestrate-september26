"""Classify financial messages using Claude Haiku text."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cache import get as cache_get, put as cache_put
from model_client import CLIENT, MODEL, call_with_retry
from prompts import MESSAGE_PROMPT, MessageResult, strip_fences

_DATASET = Path(__file__).parent.parent / "dataset"


def _call(text: str) -> MessageResult:
    msg = CLIENT.messages.create(
        model=MODEL,
        max_tokens=256,
        temperature=0,
        messages=[{"role": "user", "content": MESSAGE_PROMPT.format(message_text=text)}],
    )
    return MessageResult(**json.loads(strip_fences(msg.content[0].text)))


def run(messages_df) -> dict[str, MessageResult | None]:
    """Parse all messages. Returns None for a message that fails after retry (logged, not fatal)."""
    results: dict[str, MessageResult | None] = {}
    for _, row in messages_df.iterrows():
        message_id = row["message_id"]
        text = row["message_text"]

        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_key = f"msg:{message_id}:{text_hash}"
        cached = cache_get(cache_key)
        if cached is not None:
            results[message_id] = MessageResult(**cached)
            continue

        result = call_with_retry(lambda t=text: _call(t), message_id)
        if result is None:
            print(f"  [warn] msg {message_id} failed after retry — ignoring", file=sys.stderr)
        else:
            cache_put(cache_key, {
                "intent": result.intent,
                "new_amount": result.new_amount,
                "new_date": result.new_date,
            })
        results[message_id] = result

    return results


if __name__ == "__main__":
    import pandas as pd

    messages = pd.read_csv(_DATASET / "messages.csv", dtype=str, keep_default_na=False)
    sample = messages.head(3)

    print(f"Parsing {len(sample)} messages...")
    results = run(sample)

    for mid, r in results.items():
        print(f"  {mid}: {r}")

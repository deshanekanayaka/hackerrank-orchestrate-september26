"""Shared Anthropic client, model name, and retry wrapper."""
from __future__ import annotations
import json
import sys
import time
from typing import Any, Callable

import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"

_BACKOFF = (2, 4)  # seconds between attempts 1→2 and 2→3


def call_with_retry(fn: Callable[[], Any], label: str) -> Any | None:
    """Call fn() up to 3 times.

    Retries on malformed output (JSON/value/key errors) without delay.
    Retries on rate-limit and server errors with exponential backoff.
    Returns None when all attempts fail.
    """
    for attempt in range(3):
        try:
            return fn()
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            print(f"  [warn] {label} attempt {attempt + 1} malformed: {exc}", file=sys.stderr)
        except (anthropic.RateLimitError, anthropic.APIStatusError) as exc:
            delay = _BACKOFF[min(attempt, len(_BACKOFF) - 1)]
            print(f"  [warn] {label} attempt {attempt + 1} API error ({exc}), retrying in {delay}s", file=sys.stderr)
            if attempt < 2:
                time.sleep(delay)
    print(f"  [warn] {label} failed after 3 attempts", file=sys.stderr)
    return None

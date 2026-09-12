"""Shared Anthropic client, model name, and retry wrapper."""
from __future__ import annotations
import json
import sys
from typing import Any, Callable

import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"


def call_with_retry(fn: Callable[[], Any], label: str) -> Any | None:
    """Call fn() up to twice on malformed response. Returns None if both attempts fail."""
    for attempt in range(2):
        try:
            return fn()
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            print(f"  [warn] {label} attempt {attempt + 1} malformed: {exc}", file=sys.stderr)
    print(f"  [warn] {label} failed after retry", file=sys.stderr)
    return None

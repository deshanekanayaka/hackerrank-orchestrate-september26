"""Prompt strings and response dataclasses for all model calls."""
from __future__ import annotations
import math
import re
from dataclasses import dataclass

IMAGE_PROMPT = """You are reading a financial document image (receipt, invoice, or statement).
Extract exactly one monetary amount — the total amount due or charged.

Reply with valid JSON only, no other text:
{"amount": <number>, "currency": "<3-letter ISO 4217 code>"}

Allowed currency values: any valid ISO 4217 three-letter code (e.g. USD, EUR, GBP, INR, SGD, AUD).
amount must be a positive number. Do not include currency symbols in the amount field."""

MESSAGE_PROMPT = """You are reading a financial message. Classify its intent toward the related financial event.

Allowed intent values (pick exactly one):
- "cancel"  — the event is cancelled or should not proceed
- "amend"   — the amount or date of the event has changed
- "confirm" — the event is confirmed or acknowledged as proceeding
- "other"   — none of the above

Reply with valid JSON only, no other text:
{{"intent": "<cancel|amend|confirm|other>", "new_amount": <number or null>, "new_date": "<YYYY-MM-DD or null>"}}

Rules:
- new_amount: set to the revised amount if intent is "amend" and a new amount is stated, else null
- new_date: set to the revised date (YYYY-MM-DD) if intent is "amend" and a new date is stated, else null
- Do not infer or invent values not explicitly stated in the message

Message:
{message_text}"""


@dataclass
class ImageResult:
    amount: float
    currency: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.amount) or self.amount <= 0:
            raise ValueError(f"amount must be a finite positive number, got {self.amount}")
        self.currency = self.currency.upper()
        if len(self.currency) != 3:
            raise ValueError(f"currency must be 3-letter ISO code, got {self.currency!r}")


@dataclass
class MessageResult:
    intent: str
    new_amount: float | None
    new_date: str | None

    def __post_init__(self) -> None:
        if self.intent not in {"cancel", "amend", "confirm", "other"}:
            raise ValueError(f"intent must be one of cancel/amend/confirm/other, got {self.intent!r}")
        if self.intent != "amend":
            if self.new_amount is not None or self.new_date is not None:
                raise ValueError(f"new_amount and new_date must be null for intent={self.intent!r}")
        if self.new_date is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.new_date):
            raise ValueError(f"new_date must be YYYY-MM-DD, got {self.new_date!r}")


if __name__ == "__main__":
    import json

    r = ImageResult(**json.loads('{"amount": 123.45, "currency": "usd"}'))
    assert r.amount == 123.45 and r.currency == "USD"

    try:
        ImageResult(amount=-1, currency="USD")
    except ValueError:
        pass

    try:
        ImageResult(amount=10, currency="US")
    except ValueError:
        pass

    m = MessageResult(**json.loads('{"intent":"amend","new_amount":500,"new_date":"2026-10-01"}'))
    assert m.intent == "amend" and m.new_amount == 500 and m.new_date == "2026-10-01"

    m2 = MessageResult(**json.loads('{"intent":"other","new_amount":null,"new_date":null}'))
    assert m2.intent == "other" and m2.new_amount is None and m2.new_date is None

    try:
        MessageResult(intent="maybe", new_amount=None, new_date=None)
    except ValueError:
        pass

    print("prompts: all checks pass")
    print(f"IMAGE_PROMPT length: {len(IMAGE_PROMPT)} chars")
    print(f"MESSAGE_PROMPT length: {len(MESSAGE_PROMPT)} chars")

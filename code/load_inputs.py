"""Load and validate all dataset inputs."""
import re
import sys
from pathlib import Path
from typing import NamedTuple

import pandas as pd

# Phrases that indicate an attempt to inject instructions via message text
_ADVERSARIAL_RE = re.compile(
    r"\b(?:ignore (?:previous |all )?(?:instructions?|rules?|prompt)|"
    r"you are now|new instructions?|forget (?:everything|what)|"
    r"disregard|system prompt|act as)\b",
    re.IGNORECASE,
)

DATASET = Path(__file__).parent.parent / "dataset"

SCHEMAS: dict[str, list[str]] = {
    "financial_profiles": [
        "user_id", "home_currency", "current_available_balance",
        "minimum_balance_to_keep", "financial_priorities",
        "expense_categories_to_protect",
        "expense_categories_user_is_willing_to_reduce",
        "expense_categories_user_is_willing_to_stop",
        "payment_methods_user_will_consider", "max_installment_months",
    ],
    "financial_events": [
        "event_id", "user_id", "event_type", "description", "category",
        "direction", "amount", "currency", "event_date", "settlement_date",
        "status", "linked_event_id", "flexibility", "minimum_allowed_amount",
    ],
    "exchange_rates": ["rate_date", "from_currency", "to_currency", "rate"],
    "requests": [
        "request_id", "user_id", "request_date", "request_type",
        "requested_amount", "desired_completion_date",
        "allows_partial_payment", "request_text",
    ],
    "request_payment_options": [
        "payment_option_id", "request_id", "payment_method", "payment_amount",
        "number_of_payments", "first_payment_date", "payment_frequency_days",
        "financing_fee", "total_payable_amount",
    ],
    "messages": [
        "message_id", "user_id", "request_id", "related_event_id",
        "sent_at", "source_type", "message_text",
    ],
    "images": ["image_id", "user_id", "request_id", "related_event_id"],
}

_NUMERIC: dict[str, list[str]] = {
    "financial_profiles": ["current_available_balance", "minimum_balance_to_keep"],
    "financial_events": ["amount", "minimum_allowed_amount"],
    "exchange_rates": ["rate"],
    "requests": ["requested_amount"],
    "request_payment_options": [
        "payment_amount", "number_of_payments",
        "payment_frequency_days", "financing_fee", "total_payable_amount",
    ],
}

_DATES: dict[str, list[str]] = {
    "financial_events": ["event_date", "settlement_date"],
    "exchange_rates": ["rate_date"],
    "requests": ["request_date", "desired_completion_date"],
    "request_payment_options": ["first_payment_date"],
}


class Inputs(NamedTuple):
    profiles: pd.DataFrame
    events: pd.DataFrame
    rates: pd.DataFrame
    requests: pd.DataFrame
    options: pd.DataFrame
    messages: pd.DataFrame
    images: pd.DataFrame
    evidence_complete: dict[str, bool]


def _load_csv(name: str, path: "Path | None" = None) -> pd.DataFrame:
    p = path or (DATASET / f"{name}.csv")
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    missing = set(SCHEMAS[name]) - set(df.columns)
    if missing:
        raise ValueError(f"{p.name} missing required columns: {sorted(missing)}")
    return df[SCHEMAS[name]]


def _cast(dfs: dict[str, pd.DataFrame]) -> None:
    for name, cols in _NUMERIC.items():
        for col in cols:
            dfs[name][col] = pd.to_numeric(dfs[name][col], errors="coerce")
    for name, cols in _DATES.items():
        for col in cols:
            dfs[name][col] = pd.to_datetime(dfs[name][col], errors="coerce", utc=False)


def _check_adversarial(messages: pd.DataFrame, evidence_complete: dict[str, bool]) -> None:
    """Flag users whose messages contain instruction-injection patterns."""
    hits = messages[messages["message_text"].str.contains(_ADVERSARIAL_RE, na=False)]
    for _, row in hits.iterrows():
        evidence_complete[row["user_id"]] = False
        print(f"  [warn] adversarial pattern in {row['message_id']} (user {row['user_id']}) — marking incomplete", file=sys.stderr)


def _check_images(images: pd.DataFrame) -> dict[str, bool]:
    """Return user_id -> True when all that user's image files exist on disk."""
    result: dict[str, bool] = {}
    for _, row in images.iterrows():
        uid = row["user_id"]
        img_path = DATASET / "media" / "images" / f"{row['image_id']}.png"
        result.setdefault(uid, True)
        if not img_path.exists():
            result[uid] = False
            print(
                f"  [warn] image file missing: {img_path.name} (user {uid})",
                file=sys.stderr,
            )
    return result


def load_all(verbose: bool = True, requests_path: "Path | None" = None) -> Inputs:
    dfs: dict[str, pd.DataFrame] = {}
    for name in SCHEMAS:
        override = requests_path if name == "requests" else None
        dfs[name] = _load_csv(name, override)
        if verbose:
            print(f"  {name}: {len(dfs[name])} rows")

    _cast(dfs)

    # every request must map to a profile
    orphaned = set(dfs["requests"]["user_id"]) - set(dfs["financial_profiles"]["user_id"])
    if orphaned:
        raise ValueError(f"Requests reference users with no profile: {sorted(orphaned)}")

    evidence_complete = _check_images(dfs["images"])
    _check_adversarial(dfs["messages"], evidence_complete)

    if verbose:
        ok = sum(evidence_complete.values())
        total = len(evidence_complete)
        print(f"  evidence_complete: {ok}/{total} users have all image files present")

    return Inputs(
        profiles=dfs["financial_profiles"],
        events=dfs["financial_events"],
        rates=dfs["exchange_rates"],
        requests=dfs["requests"],
        options=dfs["request_payment_options"],
        messages=dfs["messages"],
        images=dfs["images"],
        evidence_complete=evidence_complete,
    )


if __name__ == "__main__":
    print("Loading inputs...")
    inp = load_all()
    print()
    print(f"requests:          {len(inp.requests)}")
    print(f"profiles:          {len(inp.profiles)}")
    print(f"events:            {len(inp.events)}")
    print(f"exchange rates:    {len(inp.rates)}")
    print(f"payment options:   {len(inp.options)}")
    print(f"messages:          {len(inp.messages)}")
    print(f"image refs:        {len(inp.images)}")
    users_with_images = len(inp.evidence_complete)
    users_ok = sum(inp.evidence_complete.values())
    print(f"evidence_complete: {users_ok}/{users_with_images} users")

    # spot-check types
    print()
    print("events.amount dtype:          ", inp.events["amount"].dtype)
    print("events.event_date dtype:      ", inp.events["event_date"].dtype)
    print("requests.requested_amount dtype:", inp.requests["requested_amount"].dtype)
    print("requests.request_date dtype:  ", inp.requests["request_date"].dtype)

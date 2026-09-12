"""90-day balance projection per user."""
from __future__ import annotations
import calendar
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd

FORECAST_DAYS = 90
_LOOKBACK_DAYS = 180   # how far back to look for recurrence patterns
_MIN_OCCURRENCES = 3   # minimum event count to infer recurrence

# (lo_days, hi_days, canonical_interval)
_INTERVAL_BUCKETS = [(5, 9, 7), (12, 16, 14), (25, 35, 30), (55, 100, 90)]


@dataclass
class CashFlow:
    on_date: date
    delta: float          # positive = credit, negative = debit
    event_id: str
    label: str            # category or "recurring:<category>"


@dataclass
class UserForecast:
    user_id: str
    request_date: date
    start_balance: float
    min_balance: float
    home_currency: str
    cash_flows: list[CashFlow] = field(default_factory=list)
    events_used: list[str] = field(default_factory=list)
    evidence_complete: bool = True

    def balance_on(self, d: date) -> float:
        return self.start_balance + sum(
            cf.delta for cf in self.cash_flows if cf.on_date <= d
        )

    def amount_safe_to_pay(self, requested: float) -> float:
        """Max payable on request_date without breaching min_balance over 90 days."""
        end = self.request_date + timedelta(days=FORECAST_DAYS)
        dates = sorted(set([self.request_date] + [cf.on_date for cf in self.cash_flows if self.request_date <= cf.on_date <= end]))
        min_bal = min(self.balance_on(d) for d in dates)
        return min(requested, max(0.0, min_bal - self.min_balance))

    def earliest_full_payment_date(self, requested: float, horizon: Optional[date] = None) -> Optional[date]:
        """First date where paying requested keeps balance >= min_balance from that date to horizon."""
        forecast_end = self.request_date + timedelta(days=FORECAST_DAYS)
        end = min(horizon, forecast_end) if horizon is not None else forecast_end
        dates = sorted(set([self.request_date] + [cf.on_date for cf in self.cash_flows if self.request_date <= cf.on_date <= end]))
        for i, d in enumerate(dates):
            suffix_min = min(self.balance_on(d2) for d2 in dates[i:])
            if suffix_min - requested >= self.min_balance:
                return d
        return None

    def check_safe_with_extra(self, extra: list[CashFlow], horizon: Optional[date] = None) -> bool:
        """Check that balance never falls below min_balance through horizon with extra flows added."""
        forecast_end = self.request_date + timedelta(days=FORECAST_DAYS)
        end = min(horizon, forecast_end) if horizon is not None else forecast_end
        all_flows = self.cash_flows + extra
        dates = sorted(set(
            [self.request_date]
            + [cf.on_date for cf in all_flows
               if self.request_date <= cf.on_date <= end]
        ))
        return all(
            self.start_balance + sum(cf.delta for cf in all_flows if cf.on_date <= d)
            >= self.min_balance
            for d in dates
        )


# ---------------------------------------------------------------------------
# Rate lookup helpers
# ---------------------------------------------------------------------------

def _build_rate_lookup(rates_df: pd.DataFrame) -> dict:
    lookup: dict[tuple, float] = {}
    for _, row in rates_df.iterrows():
        d = row['rate_date'].date() if hasattr(row['rate_date'], 'date') else row['rate_date']
        lookup[(d, row['from_currency'], row['to_currency'])] = float(row['rate'])
    return lookup


def _get_rate(lookup: dict, from_c: str, to_c: str, on: date) -> Optional[float]:
    candidates = [k[0] for k in lookup if k[1] == from_c and k[2] == to_c and k[0] <= on]
    if not candidates:
        return None
    return lookup[(max(candidates), from_c, to_c)]


def _to_home(amount: float, currency: str, home: str, on: date, lookup: dict) -> Optional[float]:
    if currency == home:
        return amount
    rate = _get_rate(lookup, currency, home, on)
    if rate is not None:
        return amount * rate
    # Two-hop via USD or EUR
    for mid in ('USD', 'EUR'):
        r1 = _get_rate(lookup, currency, mid, on)
        r2 = _get_rate(lookup, mid, home, on)
        if r1 is not None and r2 is not None:
            return amount * r1 * r2
    return None


# ---------------------------------------------------------------------------
# Message and OCR application
# ---------------------------------------------------------------------------

def _apply_messages(events: pd.DataFrame, messages_df: pd.DataFrame,
                    message_results: dict, user_id: str) -> pd.DataFrame:
    events = events.copy()
    user_msgs = messages_df[
        (messages_df['user_id'] == user_id) &
        (messages_df['related_event_id'].str.strip() != '')
    ]
    for _, msg in user_msgs.iterrows():
        result = message_results.get(msg['message_id'])
        if result is None:
            continue
        event_id = msg['related_event_id']
        mask = events['event_id'] == event_id
        if not mask.any():
            continue
        if result.intent == 'cancel':
            events.loc[mask, 'status'] = 'cancelled'
        elif result.intent == 'amend':
            if result.new_amount is not None:
                events.loc[mask, 'amount'] = float(result.new_amount)
            if result.new_date is not None:
                events.loc[mask, 'settlement_date'] = pd.Timestamp(result.new_date)
    return events


def _fill_ocr(events: pd.DataFrame, images_df: pd.DataFrame,
              ocr_results: dict, user_id: str) -> pd.DataFrame:
    events = events.copy()
    user_imgs = images_df[
        (images_df['user_id'] == user_id) &
        (images_df['related_event_id'].str.strip() != '')
    ]
    for _, img in user_imgs.iterrows():
        event_id = img['related_event_id']
        mask = events['event_id'] == event_id
        if not mask.any():
            continue
        if pd.isna(events.loc[mask, 'amount'].iloc[0]):
            result = ocr_results.get(img['image_id'])
            if result is not None:
                events.loc[mask, 'amount'] = result.amount
                events.loc[mask, 'currency'] = result.currency
    return events


# ---------------------------------------------------------------------------
# Recurring pattern detection and projection
# ---------------------------------------------------------------------------

def _next_month(d: date, anchor_day: int) -> date:
    month = d.month % 12 + 1
    year = d.year + (1 if d.month == 12 else 0)
    return d.replace(year=year, month=month, day=min(anchor_day, calendar.monthrange(year, month)[1]))


def _detect_interval(dates: list[date], min_count: int = _MIN_OCCURRENCES) -> Optional[int]:
    """Return canonical interval in days if pattern is consistent, else None."""
    if len(dates) < min_count:
        return None
    recent = sorted(dates)[-6:]
    if len(recent) < 2:
        return None
    intervals = [(recent[i + 1] - recent[i]).days for i in range(len(recent) - 1)]
    med = statistics.median(intervals)
    if any(abs(iv - med) > max(4, med * 0.25) for iv in intervals):
        return None
    for lo, hi, canon in _INTERVAL_BUCKETS:
        if lo <= med <= hi:
            return canon
    return None


def _infer_recurring(
    events: pd.DataFrame,
    request_date: date,
    home_currency: str,
    rates_lookup: dict,
) -> list[CashFlow]:
    """Project recurring settled cash flows into the 90-day forecast window."""
    end = request_date + timedelta(days=FORECAST_DAYS)
    lookback_start = request_date - timedelta(days=_LOOKBACK_DAYS)

    ts_lookback = pd.Timestamp(lookback_start)
    ts_request = pd.Timestamp(request_date)
    ts_end = pd.Timestamp(end)

    def _make_hist(status_list: list[str]) -> pd.DataFrame:
        df = events[
            (events['status'].isin(status_list)) &
            (events['direction'].isin(['debit', 'credit'])) &
            (events['settlement_date'].notna()) &
            (~events['amount'].isna())
        ].copy()
        df['_sd'] = df['settlement_date'].dt.normalize()
        return df[
            (df['_sd'] >= ts_lookback) &
            (df['_sd'] < ts_request + pd.Timedelta(days=60))  # include near-future scheduled
        ]

    settled_hist = _make_hist(['settled'])
    # For income: also include scheduled events (confirmed future salary)
    income_hist = _make_hist(['settled', 'scheduled'])
    income_hist = income_hist[income_hist['event_type'] == 'income']

    # Dates of existing pending/scheduled events in the forecast window (to avoid double-counting)
    existing_by_cat: dict[str, set[date]] = {}
    future_ev = events[
        events['status'].isin(['pending', 'scheduled']) &
        events['settlement_date'].notna() &
        (events['settlement_date'] >= ts_request) &
        (events['settlement_date'] <= ts_end)
    ].copy()
    for _, ev in future_ev.iterrows():
        cat = ev['category'] or ev['event_type']
        sd_ts = ev['settlement_date']
        sd = sd_ts.date() if hasattr(sd_ts, 'date') else pd.Timestamp(sd_ts).date()
        existing_by_cat.setdefault(cat, set()).add(sd)

    def _project_group(grp: pd.DataFrame, is_income: bool) -> list[CashFlow]:
        direction = grp['direction'].iloc[0]
        category = grp['category'].iloc[0]

        grp_sorted = grp.sort_values('_sd').reset_index(drop=True)

        # Convert each event amount to home currency first so outlier filtering
        # works correctly across mixed-currency groups.
        conv_list: list[float] = []
        valid_idx: list[int] = []
        for i, row in grp_sorted.iterrows():
            sd = row['_sd'].date() if hasattr(row['_sd'], 'date') else row['_sd']
            c = _to_home(float(row['amount']), row['currency'], home_currency, sd, rates_lookup)
            if c is not None:
                conv_list.append(c)
                valid_idx.append(i)
        grp_sorted = grp_sorted.iloc[valid_idx].reset_index(drop=True)
        if not conv_list:
            return []

        # Filter out amount outliers in home currency
        med_converted = statistics.median(conv_list)
        if med_converted > 0:
            keep_idx = [i for i, c in enumerate(conv_list) if med_converted * 0.5 <= c <= med_converted * 1.5]
            grp_sorted = grp_sorted.iloc[keep_idx].reset_index(drop=True)
            conv_list = [conv_list[i] for i in keep_idx]
        if grp_sorted.empty:
            return []

        date_list = [
            ts.date() if hasattr(ts, 'date') else ts
            for ts in grp_sorted['_sd'].tolist()
        ]
        min_occ = 2 if is_income else _MIN_OCCURRENCES

        # For income: cluster by day-of-month so bonus payments on different days
        # don't pollute the monthly salary interval detection.
        if is_income and len(date_list) > min_occ:
            mode_dom = Counter(d.day for d in date_list).most_common(1)[0][0]
            filtered_idx = [i for i, d in enumerate(date_list) if abs(d.day - mode_dom) <= 3]
            if len(filtered_idx) >= min_occ and len(filtered_idx) < len(date_list):
                grp_sorted = grp_sorted.iloc[filtered_idx].reset_index(drop=True)
                date_list = [date_list[i] for i in filtered_idx]
                conv_list = [conv_list[i] for i in filtered_idx]

        interval = _detect_interval(date_list, min_count=min_occ)
        if interval is None:
            return []

        last_row = grp_sorted.iloc[-1]
        last_date = date_list[-1]
        # Use median for income to be robust to one-time salary anomalies;
        # use last value for expenses (recent amounts are usually most accurate).
        converted = statistics.median(conv_list) if is_income else conv_list[-1]

        existing = existing_by_cat.get(category, set())
        result: list[CashFlow] = []
        anchor_day = last_date.day  # preserved so February clamping doesn't drift subsequent months
        next_d = _next_month(last_date, anchor_day) if interval == 30 else last_date + timedelta(days=interval)
        while next_d <= end:
            if next_d >= request_date:
                near = any(abs((next_d - ed).days) <= interval // 3 for ed in existing)
                if not near:
                    delta = converted if direction == 'credit' else -converted
                    result.append(CashFlow(
                        on_date=next_d,
                        delta=delta,
                        event_id=f"recurring:{last_row['event_id']}",
                        label=f"recurring:{category}",
                    ))
            next_d = _next_month(next_d, anchor_day) if interval == 30 else next_d + timedelta(days=interval)
        return result

    flows: list[CashFlow] = []

    # Expense/debit recurring groups (settled only)
    for (direction, category), grp in settled_hist.groupby(['direction', 'category']):
        if direction != 'debit':
            continue
        flows.extend(_project_group(grp, is_income=False))

    # Income/credit recurring groups (settled + scheduled)
    for category, grp in income_hist.groupby('category'):
        grp = grp.copy()
        grp['direction'] = 'credit'
        flows.extend(_project_group(grp, is_income=True))

    return flows


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_forecast(
    inputs,
    ocr_results: dict,
    message_results: dict,
    requests_override: Optional[pd.DataFrame] = None,
) -> dict[str, UserForecast]:
    """Build a UserForecast per request, keyed by request_id."""
    rates_lookup = _build_rate_lookup(inputs.rates)
    result: dict[str, UserForecast] = {}
    requests_df = requests_override if requests_override is not None else inputs.requests

    for _, req_row in requests_df.iterrows():
        request_id = req_row['request_id']
        user_id = req_row['user_id']
        request_date_ts = req_row['request_date']
        request_date = request_date_ts.date() if hasattr(request_date_ts, 'date') else pd.Timestamp(request_date_ts).date()

        profile_rows = inputs.profiles[inputs.profiles['user_id'] == user_id]
        if profile_rows.empty:
            continue
        profile = profile_rows.iloc[0]
        start_balance = float(profile['current_available_balance'])
        min_balance = float(profile['minimum_balance_to_keep'])
        home_currency = profile['home_currency']

        # Apply message amendments and OCR fills to this user's events
        user_events = inputs.events[inputs.events['user_id'] == user_id].copy()
        user_events = _fill_ocr(user_events, inputs.images, ocr_results, user_id)
        user_events = _apply_messages(user_events, inputs.messages, message_results, user_id)

        end_date = request_date + timedelta(days=FORECAST_DAYS)
        cash_flows: list[CashFlow] = []
        events_used: list[str] = []

        for _, ev in user_events.iterrows():
            status = ev['status']
            direction = ev['direction']
            if status in ('cancelled', 'failed', 'unrealized', 'settled'):
                continue
            if direction == 'non_cash':
                continue
            if pd.isna(ev['settlement_date']):
                continue

            sd_ts = ev['settlement_date']
            sd = sd_ts.date() if hasattr(sd_ts, 'date') else pd.Timestamp(sd_ts).date()
            if sd < request_date or sd > end_date:
                continue

            amt = ev['amount']
            if pd.isna(amt) or float(amt) <= 0:
                continue

            converted = _to_home(float(amt), ev['currency'], home_currency, sd, rates_lookup)
            if converted is None:
                continue

            # Skip single payments that exceed 5× the start balance — almost certainly
            # a total-contract value read from a document (e.g. OCR on a lease), not one payment.
            # ponytail: hard-coded 5× multiplier; calibrate if false-positives emerge
            if start_balance > 0 and converted > start_balance * 5:
                continue

            if direction == 'debit' and status in ('pending', 'scheduled'):
                delta = -converted
            elif direction == 'credit' and status == 'scheduled':
                delta = converted
            elif direction == 'credit' and status == 'pending':
                continue  # never count pending credits
            else:
                continue

            cash_flows.append(CashFlow(on_date=sd, delta=delta,
                                       event_id=ev['event_id'], label=ev.get('category', ev['event_type'])))
            events_used.append(ev['event_id'])

        # Add inferred recurring flows
        recurring = _infer_recurring(user_events, request_date, home_currency, rates_lookup)
        cash_flows.extend(recurring)
        cash_flows.sort(key=lambda cf: cf.on_date)

        result[request_id] = UserForecast(
            user_id=user_id,
            request_date=request_date,
            start_balance=start_balance,
            min_balance=min_balance,
            home_currency=home_currency,
            cash_flows=cash_flows,
            events_used=events_used,
            evidence_complete=inputs.evidence_complete.get(user_id, True),
        )

    return result


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from load_inputs import load_all

    DATASET = Path(__file__).parent.parent / 'dataset'
    inp = load_all(verbose=False)

    # Load sample requests for spot-checks
    sample_req = pd.read_csv(DATASET / 'sample_requests.csv', dtype=str, keep_default_na=False)
    # Cast numeric/date columns same as load_all
    sample_req['requested_amount'] = pd.to_numeric(sample_req['requested_amount'], errors='coerce')
    for c in ('request_date', 'desired_completion_date'):
        sample_req[c] = pd.to_datetime(sample_req[c], errors='coerce')

    forecasts = build_forecast(inp, ocr_results={}, message_results={}, requests_override=sample_req)
    print(f"Built forecasts for {len(forecasts)} requests (sample)")

    # forecasts now keyed by request_id; map user_id -> request_id for spot-checks
    uid_to_rid = {row['user_id']: row['request_id'] for _, row in sample_req.iterrows()}
    CHECKS = [
        ('user_04', 12693000, 8401800, '2024-06-15'),
        ('user_01', 25256,    25256,   '2024-03-03'),
        ('user_03', 5491000,  873000,  '2019-11-15'),
    ]
    for uid, req_amt, exp_safe, exp_date in CHECKS:
        rid = uid_to_rid.get(uid)
        if rid not in forecasts:
            print(f"  {uid}: NOT IN FORECASTS")
            continue
        fc = forecasts[rid]
        safe = fc.amount_safe_to_pay(req_amt)
        earliest = fc.earliest_full_payment_date(req_amt)
        print(f"  {uid}: safe={safe:.0f} (exp {exp_safe})  earliest={earliest} (exp {exp_date})  flows={len(fc.cash_flows)}")

"""Deterministic decision layer: produce all 8 output fields from forecast + inputs."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from forecast import CashFlow, UserForecast, FORECAST_DAYS
from load_inputs import Inputs


@dataclass
class DecisionRow:
    request_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: str  # "YYYY-MM-DD" or ""
    spending_changes_needed: str
    decision_explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_amount(x: float) -> str:
    # Round to 2 decimal places; drop trailing zeros for integers
    if abs(x - round(x)) < 0.005:
        return str(int(round(x)))
    return f"{x:.2f}"


def _accepted_methods(profile_row) -> set[str]:
    raw = profile_row['payment_methods_user_will_consider']
    if not raw or str(raw).strip() == '':
        return set()
    return set(str(raw).strip().split('|'))


def _max_installment_months(profile_row) -> Optional[int]:
    raw = profile_row['max_installment_months']
    if pd.isna(raw) or str(raw).strip() == '':
        return None
    try:
        return int(float(str(raw).strip()))
    except ValueError:
        return None


def _pipe_set(raw) -> set[str]:
    return set(str(raw).split('|')) if raw and str(raw).strip() else set()


def _check_installments(
    forecast: UserForecast, payment_dates: list[date], pay_amount: float
) -> bool:
    """Check that installment payments keep balance >= min_balance for 90 days."""
    end = forecast.request_date + timedelta(days=FORECAST_DAYS)
    extra = [
        CashFlow(d, -pay_amount, 'installment', 'installment')
        for d in payment_dates if d <= end
    ]
    return forecast.check_safe_with_extra(extra)


# ---------------------------------------------------------------------------
# Explanation builders (code-generated, never model-written)
# ---------------------------------------------------------------------------

def _expl_full_today(fc: UserForecast, amt: float, rdate: date) -> str:
    return (
        f"Pay {fc.home_currency} {_fmt_amount(amt)} in full on {rdate.isoformat()}. "
        f"Balance stays above the {fc.home_currency} {_fmt_amount(fc.min_balance)} minimum "
        f"throughout the 90-day forecast."
    )


def _expl_installments(
    fc: UserForecast, n: int, pay_amount: float, first_d: date, total: float
) -> str:
    return (
        f"Use {n} installment{'s' if n > 1 else ''} of {fc.home_currency} {_fmt_amount(pay_amount)}, "
        f"starting {first_d.isoformat()}. "
        f"Total payable: {fc.home_currency} {_fmt_amount(total)}. "
        f"Balance stays above the {fc.home_currency} {_fmt_amount(fc.min_balance)} minimum."
    )


def _expl_partial(
    fc: UserForecast, first_amt: float, second_amt: float, rdate: date, second_d: date
) -> str:
    return (
        f"Pay {fc.home_currency} {_fmt_amount(first_amt)} on {rdate.isoformat()}, "
        f"then {fc.home_currency} {_fmt_amount(second_amt)} on {second_d.isoformat()}. "
        f"Balance stays above the {fc.home_currency} {_fmt_amount(fc.min_balance)} minimum."
    )


def _expl_wait(fc: UserForecast, amt: float, rdate: date, pay_d: date) -> str:
    return (
        f"Wait until {pay_d.isoformat()}, then pay {fc.home_currency} {_fmt_amount(amt)} in full. "
        f"Paying earlier would put the {fc.home_currency} {_fmt_amount(fc.min_balance)} minimum at risk."
    )


def _expl_not_affordable(fc: UserForecast, amt: float, extra_note: str = '') -> str:
    msg = (
        f"Full payment of {fc.home_currency} {_fmt_amount(amt)} cannot be completed safely "
        f"within the 90-day forecast period while keeping the "
        f"{fc.home_currency} {_fmt_amount(fc.min_balance)} minimum balance."
    )
    if extra_note:
        msg += ' ' + extra_note
    return msg


def _expl_incomplete_evidence(fc: UserForecast, amt: float) -> str:
    return (
        f"Evidence is incomplete for this user. "
        f"Cannot safely evaluate payment of {fc.home_currency} {_fmt_amount(amt)}."
    )


def _expl_with_changes(fc: UserForecast, amt: float, pay_d: date, changes: list[str]) -> str:
    change_str = ', '.join(changes[:3])
    return (
        f"Reducing flexible spending ({change_str}) brings the balance above the "
        f"{fc.home_currency} {_fmt_amount(fc.min_balance)} minimum. "
        f"Pay {fc.home_currency} {_fmt_amount(amt)} on {pay_d.isoformat()}."
    )


# ---------------------------------------------------------------------------
# Spending changes
# ---------------------------------------------------------------------------

def _find_spending_changes(
    forecast: UserForecast,
    user_events: pd.DataFrame,
    profile_row,
    requested_amount: float,
    desired_completion: date,
) -> tuple[list[str], Optional[UserForecast]]:
    """Return (changes, modified_forecast) when spending changes enable the request, else ([], None)."""
    protected = _pipe_set(profile_row['expense_categories_to_protect'])
    stoppable = _pipe_set(profile_row['expense_categories_user_is_willing_to_stop'])
    reducible = _pipe_set(profile_row['expense_categories_user_is_willing_to_reduce'])

    # Recurring labels in the forecast (only these can be changed)
    recurring_labels = {
        cf.label for cf in forecast.cash_flows
        if cf.label.startswith('recurring:')
    }

    # Find candidate events: flexible, non-protected, in allowed categories
    candidates = []
    seen_cats: set[str] = set()
    for _, ev in user_events.sort_values('settlement_date', ascending=False).iterrows():
        if ev['status'] != 'settled':
            continue
        if ev['direction'] != 'debit':
            continue
        cat = ev['category']
        if cat in protected:
            continue
        if cat in seen_cats:
            continue
        flex = ev['flexibility']
        can_stop = flex in ('stoppable', 'reducible_or_stoppable') and cat in stoppable
        can_reduce = flex in ('reducible', 'reducible_or_stoppable') and cat in reducible

        if not (can_stop or can_reduce):
            continue
        if f"recurring:{cat}" not in recurring_labels:
            continue

        amt = ev['amount']
        if pd.isna(amt):
            continue
        min_amt_raw = ev.get('minimum_allowed_amount', float('nan'))
        min_amt = float(min_amt_raw) if not pd.isna(min_amt_raw) else 0.0

        candidates.append({
            'event_id': ev['event_id'],
            'category': cat,
            'can_stop': can_stop,
            'can_reduce': can_reduce,
            'current_amount': float(amt),
            'min_amount': min_amt,
        })
        seen_cats.add(cat)

    # Try combinations of up to 3 changes
    # Strategy: greedily try stopping the largest expenses first
    candidates.sort(key=lambda c: -c['current_amount'])

    for n in range(1, min(4, len(candidates) + 1)):
        combo = candidates[:n]
        stop_labels = set()
        change_strings = []

        for ch in combo:
            if ch['can_stop']:
                stop_labels.add(ch['category'])
                change_strings.append(f"stop:{ch['event_id']}")
            elif ch['can_reduce']:
                change_strings.append(f"reduce_to:{ch['event_id']}:{_fmt_amount(ch['min_amount'])}")

        if not change_strings:
            continue

        # Build a modified forecast with these categories stopped
        modified_flows = [
            cf for cf in forecast.cash_flows
            if not (
                cf.label.startswith('recurring:') and
                cf.label.split(':', 1)[1] in stop_labels
            )
        ]
        modified = UserForecast(
            user_id=forecast.user_id,
            request_date=forecast.request_date,
            start_balance=forecast.start_balance,
            min_balance=forecast.min_balance,
            home_currency=forecast.home_currency,
            cash_flows=sorted(modified_flows, key=lambda cf: cf.on_date),
            events_used=forecast.events_used,
            evidence_complete=forecast.evidence_complete,
        )
        earliest = modified.earliest_full_payment_date(requested_amount)
        if earliest is not None and earliest <= desired_completion:
            return change_strings, modified

    return [], None


# ---------------------------------------------------------------------------
# Per-request decision
# ---------------------------------------------------------------------------

def _decide_one(
    req_row,
    options_df: pd.DataFrame,
    forecast: UserForecast,
    profile_row,
    user_events: pd.DataFrame,
) -> DecisionRow:
    request_id = req_row['request_id']
    request_date = forecast.request_date
    requested_amount = float(req_row['requested_amount'])
    desired_ts = req_row['desired_completion_date']
    desired_completion = desired_ts.date() if hasattr(desired_ts, 'date') else pd.Timestamp(desired_ts).date()
    allows_partial = str(req_row['allows_partial_payment']).lower().strip() == 'true'

    accepted = _accepted_methods(profile_row)
    max_months = _max_installment_months(profile_row)

    # Abstain if evidence is incomplete
    if not forecast.evidence_complete:
        return DecisionRow(
            request_id=request_id,
            amount_safe_to_pay=0.0,
            affordability_status='not_affordable',
            recommended_payment_method='not_recommended',
            payment_plan='none',
            earliest_date_for_full_payment='',
            spending_changes_needed='none',
            decision_explanation=_expl_incomplete_evidence(forecast, requested_amount),
        )

    amount_safe = forecast.amount_safe_to_pay(requested_amount)
    earliest_full = forecast.earliest_full_payment_date(requested_amount)
    earliest_full_str = earliest_full.isoformat() if earliest_full else ''

    req_opts = options_df[options_df['request_id'] == request_id].copy()

    # --- 1. Full payment today (affordable_now) ---
    if 'full_payment' in accepted and amount_safe >= requested_amount:
        return DecisionRow(
            request_id=request_id,
            amount_safe_to_pay=requested_amount,
            affordability_status='affordable_now',
            recommended_payment_method='full_payment',
            payment_plan=f"{request_date.isoformat()}:{_fmt_amount(requested_amount)}",
            earliest_date_for_full_payment=request_date.isoformat(),
            spending_changes_needed='none',
            decision_explanation=_expl_full_today(forecast, requested_amount, request_date),
        )

    # Determine if a zero-cost plan (full_payment cost == requested_amount) is viable.
    # If so, prefer it over installments that carry a financing fee.
    _wait_viable = (
        'full_payment' in accepted and
        earliest_full is not None and
        earliest_full > request_date and
        earliest_full <= desired_completion
    )
    _partial_viable = (
        'partial_payment' in accepted and
        allows_partial and
        0.0 < amount_safe < requested_amount and
        earliest_full is not None and earliest_full <= desired_completion
    )

    # --- 2. Installments — only when no cheaper (no-fee) plan fits ---
    if 'installments' in accepted:
        inst_opts = req_opts[req_opts['payment_method'] == 'installments'].sort_values(
            'payment_option_id'
        )
        for _, opt in inst_opts.iterrows():
            n_raw = opt['number_of_payments']
            n = int(float(n_raw)) if n_raw and str(n_raw).strip() else 1
            if max_months is not None and n > max_months:
                continue

            first_ts = opt['first_payment_date']
            first_d = first_ts.date() if hasattr(first_ts, 'date') else pd.Timestamp(str(first_ts)).date()
            freq_raw = opt['payment_frequency_days']
            freq = int(float(freq_raw)) if freq_raw and str(freq_raw).strip() else 30
            pay_amount = float(opt['payment_amount'])
            total_payable = float(opt['total_payable_amount'])

            pay_dates = [first_d + timedelta(days=freq * i) for i in range(n)]
            if pay_dates[-1] > desired_completion:
                continue
            if not _check_installments(forecast, pay_dates, pay_amount):
                continue

            # Skip this installment option if a cheaper no-fee plan is also viable
            if total_payable > requested_amount * 1.001 and (_wait_viable or _partial_viable):
                continue

            plan = '|'.join(f"{d.isoformat()}:{_fmt_amount(pay_amount)}" for d in pay_dates)
            return DecisionRow(
                request_id=request_id,
                amount_safe_to_pay=amount_safe,
                affordability_status='affordable_with_plan',
                recommended_payment_method='installments',
                payment_plan=plan,
                earliest_date_for_full_payment=earliest_full_str,
                spending_changes_needed='none',
                decision_explanation=_expl_installments(forecast, n, pay_amount, first_d, total_payable),
            )

    # --- 3. Wait for full payment (affordable_later, fewer payments than partial) ---
    if _wait_viable:
        plan = f"{earliest_full.isoformat()}:{_fmt_amount(requested_amount)}"
        return DecisionRow(
            request_id=request_id,
            amount_safe_to_pay=amount_safe,
            affordability_status='affordable_later',
            recommended_payment_method='wait',
            payment_plan=plan,
            earliest_date_for_full_payment=earliest_full_str,
            spending_changes_needed='none',
            decision_explanation=_expl_wait(forecast, requested_amount, request_date, earliest_full),
        )

    # --- 4. Partial payment (affordable_with_plan) ---
    if _partial_viable:
        remaining = requested_amount - amount_safe
        plan = (
            f"{request_date.isoformat()}:{_fmt_amount(amount_safe)}|"
            f"{earliest_full.isoformat()}:{_fmt_amount(remaining)}"
        )
        return DecisionRow(
            request_id=request_id,
            amount_safe_to_pay=amount_safe,
            affordability_status='affordable_with_plan',
            recommended_payment_method='partial_payment',
            payment_plan=plan,
            earliest_date_for_full_payment=earliest_full_str,
            spending_changes_needed='none',
            decision_explanation=_expl_partial(forecast, amount_safe, remaining, request_date, earliest_full),
        )

    # --- 5. Spending changes (affordable_with_plan or affordable_later) ---
    changes, modified = _find_spending_changes(
        forecast, user_events, profile_row, requested_amount, desired_completion
    )
    if changes and modified is not None:
        earliest_mod = modified.earliest_full_payment_date(requested_amount)
        if earliest_mod is not None:
            plan = f"{earliest_mod.isoformat()}:{_fmt_amount(requested_amount)}"
            changes_str = '|'.join(changes)
            status = 'affordable_with_plan' if earliest_mod <= desired_completion else 'affordable_later'
            return DecisionRow(
                request_id=request_id,
                amount_safe_to_pay=amount_safe,
                affordability_status=status,
                recommended_payment_method='wait' if earliest_mod > request_date else 'full_payment',
                payment_plan=plan,
                earliest_date_for_full_payment=earliest_mod.isoformat(),
                spending_changes_needed=changes_str,
                decision_explanation=_expl_with_changes(forecast, requested_amount, earliest_mod, changes),
            )

    # --- 6. Not affordable ---
    note = ''
    if earliest_full is not None:
        note = f"Earliest safe date ({earliest_full.isoformat()}) is after the desired completion date."
    return DecisionRow(
        request_id=request_id,
        amount_safe_to_pay=amount_safe,
        affordability_status='not_affordable',
        recommended_payment_method='not_recommended',
        payment_plan='none',
        earliest_date_for_full_payment=earliest_full_str,
        spending_changes_needed='none',
        decision_explanation=_expl_not_affordable(forecast, requested_amount, note),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def decide_all(inputs: Inputs, forecasts: dict[str, UserForecast]) -> list[dict]:
    """Produce one output row dict per request in inputs.requests."""
    rows = []
    for _, req_row in inputs.requests.iterrows():
        user_id = req_row['user_id']
        forecast = forecasts.get(user_id)
        if forecast is None:
            # Should not happen if load_all ran cleanly; produce a safe default
            rows.append({
                'request_id': req_row['request_id'],
                'amount_safe_to_pay': 0,
                'affordability_status': 'not_affordable',
                'recommended_payment_method': 'not_recommended',
                'payment_plan': 'none',
                'earliest_date_for_full_payment': '',
                'spending_changes_needed': 'none',
                'decision_explanation': 'No forecast available for this user.',
            })
            continue

        profile_rows = inputs.profiles[inputs.profiles['user_id'] == user_id]
        profile_row = profile_rows.iloc[0]
        user_events = inputs.events[inputs.events['user_id'] == user_id]

        decision = _decide_one(req_row, inputs.options, forecast, profile_row, user_events)
        rows.append(decision.to_dict())

    return rows


# ---------------------------------------------------------------------------
# Self-test against sample_requests.csv
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from load_inputs import load_all
    from forecast import build_forecast

    DATASET = Path(__file__).parent.parent / 'dataset'

    inp = load_all(verbose=False)
    sample = pd.read_csv(DATASET / 'sample_requests.csv', dtype=str, keep_default_na=False)

    INPUT_COLS = ['request_id', 'user_id', 'request_date', 'request_type',
                  'requested_amount', 'desired_completion_date', 'allows_partial_payment', 'request_text']
    sample_inp = inp._replace(requests=pd.read_csv(
        DATASET / 'sample_requests.csv', dtype=str, keep_default_na=False
    )[INPUT_COLS])
    forecasts = build_forecast(sample_inp, ocr_results={}, message_results={})
    rows = decide_all(sample_inp, forecasts)
    decisions = {r['request_id']: r for r in rows}

    # Compare against sample (already loaded above)
    FIELDS = [
        'affordability_status', 'recommended_payment_method',
        'amount_safe_to_pay', 'earliest_date_for_full_payment',
    ]
    correct = {f: 0 for f in FIELDS}
    total = len(sample)

    print(f"\n{'request_id':<15} {'field':<35} {'expected':<30} {'got':<30} {'ok'}")
    print('-' * 120)
    def _fields_match(f, exp, act):
        if f == 'amount_safe_to_pay':
            try:
                return abs(float(exp) - float(act)) < 0.02
            except (ValueError, TypeError):
                return exp == act
        return exp == act

    for _, row in sample.iterrows():
        rid = row['request_id']
        got = decisions.get(rid, {})
        for f in FIELDS:
            expected = str(row.get(f, '')).strip()
            actual = str(got.get(f, '')).strip()
            ok = _fields_match(f, expected, actual)
            if ok:
                correct[f] += 1
            mark = 'Y' if ok else 'N'
            if not ok:
                print(f"{rid:<15} {f:<35} {expected:<30} {actual:<30} {mark}")

    print('\n--- Accuracy ---')
    for f in FIELDS:
        pct = correct[f] / total * 100
        print(f"  {f:<40} {correct[f]:2}/{total}  {pct:.0f}%")

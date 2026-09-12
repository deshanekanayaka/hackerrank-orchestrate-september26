# 05 — Limits

## 1. amount_safe_to_pay is wrong for most requests

We score 4 out of 25 on `amount_safe_to_pay`. Our value is consistently higher than gold. Gold projects more expenses than we do. We infer recurring patterns from a 180-day lookback at 7-day, 14-day, 30-day, and 90-day intervals. Gold appears to use a different set of projected expenses. We cannot close this gap without knowing gold's projection algorithm. With more time, we test shorter lookback windows and compare projected cash-flow counts per user against the implied gap.

## 2. 10-day and 21-day recurring patterns are not detected

Users 03 and 18 have expenses on 10-day and 21-day cycles. Our interval buckets do not include these. We tried adding them. They fixed requests 03 and 18 but broke user 25. Adding the 10-day bucket projects a grocery expense that gold does not project. We do not know why gold skips that projection. We reverted the change. With more time, we inspect the full 250-request dataset to weigh the fix against the breakage.

## 3. Salary amendments without a linked event are ignored

Message parsing works: we extract intent, amount, and date from every message. We apply amendments only to events with a `related_event_id`. Several messages describe future salary changes without referencing a specific event row. Our recurring pattern often produces the right salary because the amended amount matches the historical median. If it does not match, our forecast is wrong and we cannot detect it at runtime.

## 4. Exchange rate staleness at month boundaries

We use the most recent dated rate at or before the settlement date. The exchange rate table has sparse coverage at some month boundaries. If a rate changes significantly on a date with no table entry, we use a stale rate. We have not audited how far apart the rate dates are or whether this affects any of the 250 requests. With more time, we log the rate-date gap for every foreign-currency conversion and flag gaps over 7 days.

## 5. No unit tests on the decision layer

The self-test in `code/decide.py` runs only against the 25 labelled sample requests. We have no tests for individual branches in `_decide_one`. The spending-changes path, the installment option selection, and the partial-payment construction have no isolated tests. A rule change in one branch breaks other requests silently.

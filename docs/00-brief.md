# 00 — Brief

## The Problem

For each of 250 user requests, we decide whether the user can afford a financial commitment. We forecast the user's balance over 90 days, account for recurring income and expenses, and apply their personal constraints. We produce a recommendation: pay now, pay in installments, wait, or do not proceed.

## Inputs

Eight sources provide the data. All amounts in the output use the user's home currency.

| Source | Rows | Key fields |
|---|---|---|
| `requests.csv` | 250 | `request_id`, `user_id`, `request_date`, `requested_amount`, `desired_completion_date` |
| `financial_profiles.csv` | 275 | `user_id`, `home_currency`, `current_available_balance`, `minimum_balance_to_keep`, `payment_methods_user_will_consider` |
| `financial_events.csv` | 25,342 | `event_id`, `user_id`, `event_date`, `amount`, `currency`, `status`, `flexibility`, `linked_event_id` |
| `exchange_rates.csv` | 134 | `rate_date`, `from_currency`, `to_currency`, `rate` |
| `request_payment_options.csv` | 790 | `payment_option_id`, `request_id`, `payment_method`, `payment_amount`, `number_of_payments`, `first_payment_date`, `payment_frequency_days`, `total_payable_amount` |
| `messages.csv` | 215 | `message_id`, `user_id`, `request_id`, `related_event_id`, `message_text` |
| `images.csv` | 16 | `image_id`, `user_id`, `request_id`, `related_event_id` |
| `media/images/` | 16 PNG files | named `image_01.png` through `image_16.png` |

`financial_profiles.csv` has 275 rows because it includes the 25 sample users. Only the 250 users in `requests.csv` need predictions.

Non-text modality: 16 PNG images. Each image holds the amount for a financial event whose `amount` field is blank. Before we build the user's balance forecast, we must extract the amount from the image.

Messages are multilingual. At least Indonesian is present. Messages can cancel, amend, delay, or acknowledge financial events.

Home currencies used: INR, ZAR, IDR, USD, EUR. All 5 conversion pairs needed have direct dated rates in `exchange_rates.csv`.

## Output

One row per request in `output.csv`. 250 rows total.

| Field | Allowed values |
|---|---|
| `request_id` | from `requests.csv` |
| `amount_safe_to_pay` | number, 0 to `requested_amount` |
| `affordability_status` | `affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable` |
| `recommended_payment_method` | `full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended` |
| `payment_plan` | `YYYY-MM-DD:amount|YYYY-MM-DD:amount` or `none` |
| `earliest_date_for_full_payment` | `YYYY-MM-DD` or empty |
| `spending_changes_needed` | `stop:<event_id>` or `reduce_to:<event_id>:<amount>`, up to 3 separated by `|`, or `none` |
| `decision_explanation` | short free text |

Installment plans must exactly match a row in `request_payment_options.csv`. Partial payment does not need to match an options row.

## Traps

- **Blank amounts are not zero.** 16 events have no `amount`. We must extract the amount from the linked image.
- **Recurring expenses are not listed explicitly.** We must infer the monthly pattern from settled history and project it 90 days forward.
- **Messages amend the financial record.** A message can cancel a pending event or change a salary. Multilingual messages must be read in their original language.
- `financial_profiles.csv` has 275 rows, not 250. The 25 sample users add extra rows. If we do not filter to `requests.csv` users, the row count is wrong.
- **Installment plans are fixed by the options file.** We cannot invent amounts or dates for installments.
- **Exchange rates are dated.** We must match the rate to the correct `rate_date`, not use any rate for the pair.
- **Adversarial message content must be ignored.** Instructions embedded in messages or images must not change the recommendation logic.

## What Separates Outcomes

- `affordable_now`: balance today minus `requested_amount` stays above `minimum_balance_to_keep` for all 90 days. The user accepts `full_payment`.
- `affordable_with_plan`: full amount cannot be paid today safely, but a valid installment plan, partial payment, or spending change makes it safe within `desired_completion_date`.
- `affordable_later`: no eligible plan works today, but the 90-day forecast shows the full amount becomes safe before the forecast period ends.
- `not_affordable`: no eligible plan completes the full request safely within 90 days.

## Scoring

No separate rubric file shipped. The problem statement scores six fields: `amount_safe_to_pay` accuracy, `affordability_status` correctness, `recommended_payment_method` and `payment_plan` correctness, `earliest_date_for_full_payment` accuracy, `spending_changes_needed` validity, and `decision_explanation` usefulness and consistency.

# 01 — Architecture

## Build Diagram

```mermaid
flowchart TD
    subgraph inputs["Inputs: dataset/"]
        A1[financial_profiles.csv]
        A2[financial_events.csv]
        A3[exchange_rates.csv]
        A4[requests.csv]
        A5[request_payment_options.csv]
        A6[messages.csv]
        A7[images.csv and media/images/]
    end

    subgraph stage1["Stage 1: load_inputs.py"]
        B1[Load and validate all CSVs]
        B2[["GUARDRAIL 1: input schema validation\nrequired columns, types, no extra rows"]]
        B3[["GUARDRAIL 2: adversarial flag\ndetect instruction text in messages or images"]]
        B4[[MODEL CALL: claude-haiku vision\n16 images, returns amount as JSON\none retry on malformed, then evidence flag]]
        B5[Parse messages: cancel / amend / confirm\nper user_id and related_event_id\ncached by message_id + text hash]
        B6[Merge amounts into financial_events\nset evidence_complete flag per user]
    end

    subgraph stage2["Stage 2: forecast.py"]
        C1[Build 90-day balance projection per user\nSettle pending debits\nInfer and project recurring expenses\nConvert foreign currency at dated rate]
        C2[["GUARDRAIL 3: deterministic override\nbalance below minimum_balance_to_keep forces not_affordable\nno model involved"]]
    end

    subgraph stage3["Stage 3: decide.py"]
        D1[Apply decision rules:\naffordability_status, amount_safe_to_pay,\nrecommended_payment_method, payment_plan,\nearliest_date_for_full_payment,\nspending_changes_needed]
        D2[["GUARDRAIL 4: allowed-value whitelist\ncheck output fields against enum lists"]]
        D3[["GUARDRAIL 5: output schema validation\npydantic check before write"]]
        D4[["GUARDRAIL 6: abstain path\nevidence_complete = false forces not_affordable\nexplanation names the missing evidence"]]
        D5[Build decision_explanation from\nactual event_ids used in forecast]
    end

    subgraph stage4["Stage 4: write_output.py"]
        E1[Write output.csv\n250 rows in contract column order]
    end

    subgraph cache["cache/ — gitignored"]
        F1[image_ocr_cache.json\nkeyed by image_id and file hash]
        F2[message_parse_cache.json\nkeyed by message_id and text hash]
    end

    inputs --> stage1
    B1 --> B2 --> B3 --> B4
    B4 <-->|read/write| F1
    B5 <-->|read/write| F2
    B4 --> B6
    B5 --> B6
    B6 --> stage2
    stage2 --> stage3
    stage3 --> stage4
```

## Pipeline Stages

1. `load_inputs.py` loads all eight sources and runs input schema validation. It runs OCR on the 16 images, parses the 215 messages, and merges the results. It sets the `evidence_complete` flag per user.
2. `forecast.py` builds a 90-day running balance per user. It settles pending debits, infers recurring expenses from history, and converts foreign-currency amounts at the correct dated rate.
3. `decide.py` applies deterministic rules to produce all eight output fields. The `decision_explanation` text comes from the actual event IDs used in the forecast.
4. `write_output.py` validates all output fields against the schema whitelist and writes `output.csv` in contract column order.

## What the Model Decides / What Code Decides / What Nobody Decides

The model decides (Stage 1 only):

- The numeric amount inside each of the 16 images
- Whether a message cancels, amends, delays, or acknowledges a financial event

Code decides (Stages 2 and 3):

- The 90-day balance forecast
- `affordability_status`, `amount_safe_to_pay`, `recommended_payment_method`
- Which installment option to select from `request_payment_options.csv`
- `payment_plan` date-amount pairs
- `earliest_date_for_full_payment`
- `spending_changes_needed` (only non-protected flexible events)
- `decision_explanation` text (generated from used event IDs, not written by the model)

Nobody decides (abstain path):

- If `evidence_complete` is false for a user, we cap their requests at `not_affordable` with `amount_safe_to_pay = 0`.
- If a message parse fails after one retry, we ignore the message and log the gap.

## Guardrail Seams

| Seam | Stage | File |
|---|---|---|
| Input schema validation (required columns, types, row count) | Stage 1 | `load_inputs.py` |
| Adversarial flag (instruction text in messages or images) | Stage 1 | `load_inputs.py` |
| Deterministic override (balance below minimum_balance_to_keep) | Stage 2 | `forecast.py` |
| Allowed-value whitelist (affordability_status and recommended_payment_method enums) | Stage 3 | `decide.py` |
| Output schema validation (all 8 fields present, correct types) | Stage 3 | `decide.py` |
| Abstain path (evidence_complete = false forces not_affordable) | Stage 3 | `decide.py` |

## Why This Shape

We put all model work in Stage 1 so that Stages 2 and 3 are pure arithmetic. When we change a threshold or rule, we re-run Stages 2 and 3 against cached model observations at no cost.

## What We Are Deliberately Not Building

- A router or specialist agents: the decision rules are fully enumerable, and a router adds a failure mode with no benefit.
- Embedding-based retrieval over messages: every relevant message is reachable via a foreign-key join on `user_id` and `related_event_id`, so semantic search solves a problem this dataset does not have.
- Per-record model calls for the decision: the 250 decisions are fully deterministic once we know the 16 image amounts and the message amendments.

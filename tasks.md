# tasks.md

Maintained by Claude Code. This file plus `docs/` rebuilds lost context after a session reset.

**H0**: {{clock time}}
**H24**: {{clock time}}

---

## Next action

Stage 5: build `code/forecast.py` and `code/decide.py`, the deterministic decision layer.

## In progress

- [ ] Stage 5: deterministic decision layer

## Blocked

- [ ]

## Done

- [x] Stage 4: model call layer (`code/ocr.py`, `code/parse_messages.py`). Real Haiku calls on 2 images and 3 messages verified. Cache replay confirmed identical output.
- [x] Stage 3: prompt layer (`code/prompts.py`). IMAGE_PROMPT, MESSAGE_PROMPT, ImageResult, MessageResult dataclasses. All checks pass.
- [x] Stage 2: response cache and replay (`code/cache.py`). SHA-256 keyed, one JSON file per entry in `cache/`, get/put pass self-test.
- [x] Stage 1: loader and input validation (`code/load_inputs.py`). Results: 250 requests, 275 profiles, 25342 events, 16 images, all files present.

---

## Phase checklist

### H0-H2 Understand
- [ ] Read the problem statement twice, alone
- [ ] Read the platform AGENTS.md
- [ ] If a scoring rubric or evaluation criteria file is present, read it
- [ ] Input audit complete
- [ ] `docs/00-brief.md` written
- [ ] I can say what goes in and what comes out

### H2-H4 Architecture (my decisions)
- [ ] PLAYBOOK.md read
- [ ] Options presented for all nine decisions
- [ ] D0 model decides versus code decides: chosen
- [ ] D1 pipeline shape: chosen
- [ ] D2 model calls per record: chosen
- [ ] D3 deterministic versus model routing: chosen
- [ ] D4 retrieval: chosen
- [ ] D5 confidence: chosen
- [ ] D6 non-text input handling (if applicable): chosen
- [ ] D7 abstain policy: chosen
- [ ] D8 evaluation approach: chosen
- [ ] D9 model tiering: chosen
- [ ] D10 evidence verification: chosen
- [ ] `docs/01-architecture.md` written with Mermaid build diagram
- [ ] `docs/02-decisions.md` opened with one entry per decision
- [ ] I can name the stages in order and point at the diagram

### H4-H10 Build
- [x] 1 loader and input validation
- [x] 2 response cache and replay
- [x] 3 prompt layer with allowed values enumerated
- [ ] 4 model call returning observations only
- [ ] 5 deterministic decision layer
- [ ] 6 evaluation script, per-field accuracy
- [ ] 7 guardrails: schema, whitelist, retry, overrides, abstain
- [ ] 8 evidence verification (if output cites sources)
- [ ] 9 adversarial input detectors
- [ ] 10 concurrency cap and backoff
- [ ] Two consecutive runs produce identical output
- [ ] Iteration 1 measured, logged
- [ ] Iteration 2 measured, logged
- [ ] Iteration 3 measured, logged
- [ ] Build diagram still matches the code
- [ ] End-to-end run produces a valid output artifact
- [ ] Committed and pushed
- [ ] Next action set for wake-up

### H10-H16 Sleep
- [ ] Two alarms set
- [ ] Actually slept

### H16-H20 Harden
- [ ] Read architecture and decisions docs before coding
- [ ] Full run on all records
- [ ] Output reviewed: counts, duplicates, allowed values, ranges, empty fields
- [ ] 20 records sampled and reviewed
- [ ] Guardrail audit against the six seams
- [ ] Adversarial input review: embedded instructions, pressure language, mixed languages
- [ ] Major issues fixed
- [ ] `/ponytail-review` run, flagged code removed
- [ ] `/ponytail-audit` run, flagged code removed
- [ ] `docs/03-trace.md` written
- [ ] `docs/04-production.md` written with production diagram
- [ ] `docs/05-limits.md` written
- [ ] `docs/06-future.md` written with extension diagram
- [ ] `docs/07-evaluation.md` written with per-field numbers and iterations

### H20-H21 Read
- [ ] Architecture doc read out loud
- [ ] Trace doc read out loud
- [ ] Decisions, production, future, limits, evaluation read
- [ ] I re-explained everything I stumbled on
- [ ] I fixed anything wrong in the docs

### H21-H23 Ship
- [ ] Output artifact verified against the problem statement
- [ ] README rewritten for a cold judge: build diagram, eval numbers, cost table
- [ ] Honesty note added to README
- [ ] Packaged
- [ ] Submitted
- [ ] Submission accepted by platform

### H23-H24 Buffer
- [ ] Trace and production docs read once more

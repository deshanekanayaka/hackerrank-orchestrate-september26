# tasks.md

Maintained by Claude Code. Survives session resets — this file plus `docs/` rebuilds lost context.

**H0**: {{clock time}}
**H24**: {{clock time}}

---

## Next action

_One specific line. File, function, or command. Updated at the end of every loop._

>

## In progress

- [ ] 

## Blocked

- [ ] 

## Done

_Rolled up, not a transcript._

- [ ] 

---

## Phase checklist

### H0-H2 Understand
- [ ] Read the problem statement twice, alone
- [ ] Read the platform AGENTS.md
- [ ] Checked for a scoring rubric / evaluation criteria file, and read it if present
- [ ] Input audit complete
- [ ] `docs/00-brief.md` written
- [ ] I can say what goes in and what comes out

### H2-H4 Architecture (my decisions)
- [ ] PLAYBOOK.md read
- [ ] Options presented for all nine decisions
- [ ] D0 model decides versus code decides — chosen
- [ ] D1 pipeline shape — chosen
- [ ] D2 model calls per record — chosen
- [ ] D3 deterministic versus model routing — chosen
- [ ] D4 retrieval — chosen
- [ ] D5 confidence — chosen
- [ ] D6 non-text input handling (if applicable) — chosen
- [ ] D7 abstain policy — chosen
- [ ] D8 evaluation approach — chosen
- [ ] D9 model tiering — chosen
- [ ] D10 evidence verification — chosen
- [ ] `docs/01-architecture.md` written with Mermaid build diagram
- [ ] `docs/02-decisions.md` opened with one entry per decision
- [ ] I can name the stages in order and point at the diagram

### H4-H10 Build
- [ ] 1 loader and input validation
- [ ] 2 response cache and replay
- [ ] 3 prompt layer with allowed values enumerated
- [ ] 4 model call returning observations only
- [ ] 5 deterministic decision layer
- [ ] 6 evaluation harness, per-field accuracy
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
- [ ] 20 records sampled and checked
- [ ] Guardrail audit against the six seams
- [ ] Adversarial input check: embedded instructions, pressure language, mixed languages
- [ ] Top issues fixed
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
- [ ] Everything I stumbled on has been re-explained
- [ ] Anything wrong in the docs has been fixed

### H21-H23 Ship
- [ ] Output artifact verified against the problem statement
- [ ] README rewritten for a cold judge: build diagram, eval numbers, cost table
- [ ] Honesty note added to README
- [ ] Packaged
- [ ] Submitted
- [ ] Confirmation received

### H23-H24 Buffer
- [ ] Trace and production docs read once more

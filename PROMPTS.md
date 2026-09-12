# PROMPTS — Copy and paste

Self-contained. None assumes earlier conversation. Nothing assumes a language, data format, or problem domain.

---

## Phase kickoffs

### H0-H2 — Understand

```
Read the problem statement and inventory every input the challenge provides. Do not write pipeline code and do not propose an architecture yet.

Audit the inputs: what sources exist, how many records, the structure and types of each, missing values, the key fields and their formats, and the relationships between sources. Then tell me every identifier format mismatch that would break a naive join, every field name reused with a different meaning across sources, any non-text modality present and what handling it needs, and anything that would break a naive per-record loop.

Also check whether this edition ships a scoring rubric or evaluation criteria file alongside the problem statement. If it does, read it and summarise how we are scored as a section in docs/00-brief.md.

Then write docs/00-brief.md following DOCS-SPEC.md.

Then stop. Tell me in five sentences what this problem actually is and what the three worst traps are.
```

### H2-H4 — Architecture options (you decide)

```
Time to design the pipeline. I am making the architectural calls, so give me options rather than a single answer.

Read PLAYBOOK.md first. Treat those patterns as priors and tell me explicitly where this problem argues against any of them.

Present each of these decisions in the format from CLAUDE.md — the decision in one line, then 2 or 3 viable options each with what it is, build time cost, what breaks under it, and how hard it is for me to defend at interview, then your recommendation and what would change it:

0. Division of labour: what the model decides versus what deterministic code decides
1. Pipeline shape: how many stages and where the boundaries fall
2. Model calls per record: one call, or a multi-stage split
3. Routing: deterministic rules versus model-driven decisions, and where each applies
4. Retrieval: none, keyword, embeddings, or hybrid
5. Confidence: how it gets set and when it gets capped
6. Non-text inputs, if this problem has any: how we handle them
7. Abstain policy: when the system refuses to answer rather than guessing
8. Evaluation: what we measure against the labelled examples and how often
9. Model tiering: whether a cheap model or deterministic rule handles easy records before the expensive model sees them
10. Evidence verification: if our output claims to rest on specific sources, how we check mechanically that those sources were really consulted and really say that

If a scoring rubric shipped with this edition, cross-check every recommendation against it and tell me where the rubric argues for a different choice.

Do all eleven in one message so I can see how they interact. I will choose, then you write the docs.
```

### H2-H4 — Lock the architecture after choosing

```
Here are my choices: {{list them, one line each}}.

Now write docs/01-architecture.md following DOCS-SPEC.md. Include the Mermaid build diagram showing every stage, the data flow, where the model is called, and where each of the six guardrails sits. Only put components in the diagram that will actually exist in the repo.

Then open docs/02-decisions.md with one entry per decision above, recording what I chose, what you recommended, and why.

Then stop and walk me through the architecture in five sentences.
```

### H4-H10 — Build

```
Build the pipeline stage by stage, following the loop in CLAUDE.md: plan, implement, test, review.

Build in this order, adapting names to what this problem actually needs:
1. Loader and input validation
2. Response cache and replay - every model response saved to disk keyed by input, replayed on re-run unless the input changed. Build this before any real model calls.
3. Prompt layer with every allowed value enumerated
4. The model call, returning observations only
5. Deterministic decision layer that turns observations into the final answer
6. Evaluation harness against the labelled examples, reporting per-field accuracy
7. Guardrails: schema validation, value whitelist, retry, deterministic overrides, abstain
8. Evidence verification, if the output claims to rest on specific sources
9. Adversarial input detectors, running before the model call
10. Concurrency cap and backoff

One stage at a time. Do not start the next until I say go. After each REVIEW beat, append the decision to docs/02-decisions.md, update the build diagram in docs/01-architecture.md if the shape changed, and update tasks.md.

Test means running real code on real records and showing me actual output, not describing what it should do.

Start with stage 1.
```

### H16-H20 — Harden

```
Run the pipeline on the full input set. Then review the output like a reviewer who has never seen this project.

Show me: record count against input count, any duplicate keys, any value outside the allowed set, any out-of-range numbers, any required field left empty. Then sample 20 records, 10 routine and 10 that look wrong, and for each of the wrong-looking ones tell me what the input was, what we produced, and whether it is actually correct.

Then audit the code for missing guardrails against the six seams in docs/01-architecture.md.

Report everything. Fix nothing yet.
```

### H16-H20 — Remaining docs and diagrams

```
Write docs/03-trace.md, docs/04-production.md, docs/05-limits.md and docs/06-future.md following DOCS-SPEC.md.

For the trace, pick a real record that exercises at least one guardrail, not the easiest one.

For production, open with the Mermaid production diagram at scale. Use load balancing, stateless workers, queues with background workers, caching, read replicas, connection pooling and sharding only where they genuinely apply to this problem. Label it clearly as target state and say in one line underneath what we actually shipped.

For future, give me a staged extension path from what we built, each stage naming what we add, what it unlocks, what has to change in existing code, and rough effort. End with a Mermaid diagram of the extended system showing where today's pipeline sits inside it.

Be honest in limits. Do not pad with generic caveats.
```

### H21-H23 — Ship

```
Final submission pass. Open the output artifact as if you had never seen this project, and check it against the problem statement exactly: field names and order, one record per input record, no duplicate keys, every value within its allowed set, every number in range, and any explanation field actually explaining rather than padding.

Then rewrite the README at repo root so a judge can clone this and run it in five minutes: setup steps, runtime version, dependencies, environment variables, the single run command, and what the program reads and writes. Include the build diagram from docs/01-architecture.md.

Report issues first. Fix them one at a time after I confirm.
```

---

## Evaluation prompts

### Measure, then pick the next change

```
Run the evaluation harness and show me per-field accuracy. Then tell me which single field has the most room to improve and what one change would move it. Do not make the change yet.
```

### After each iteration

```
Re-run the harness. Show me the before and after numbers for the field we targeted, and whether any other field regressed. Then append an iteration entry to docs/07-evaluation.md with the change, the field, and both numbers.
```

### Try and measure an alternative

```
We are currently doing {{CURRENT APPROACH}} for {{FIELD OR STAGE}}. Implement {{ALTERNATIVE}} behind a flag, run the harness both ways, and show me the per-field numbers side by side. Recommend which to keep and why. Keep both until I decide.
```

### Adversarial input check

```
Check how the pipeline handles adversarial inputs: instructions embedded in text, instructions embedded in media if this problem has media, escalation or pressure language, and mixed languages. For each, tell me whether we detect it, whether detection happens before the model call, and whether it changes the verdict when it should only raise a flag. Report first, fix after I confirm.
```

### Cost and latency numbers

```
Give me the cost and latency table for a full run: model calls per record, records skipped by cheap gates, estimated cost at current pricing, and wall-clock runtime. Use real measurements from the last run, not estimates, wherever you have them.
```

---

## Diagram prompts

### Redraw the build diagram after a shape change

```
The pipeline shape changed. Redraw the Mermaid build diagram in docs/01-architecture.md to match the current code exactly. Every node must correspond to something that exists in the repo. Mark the model call distinctly and show where each of the six guardrails sits. Then tell me in five sentences what changed and why.
```

### Production diagram on its own

```
Draw a Mermaid diagram of this system running at real scale, as target state rather than what we shipped.

Include only what genuinely applies to this problem: a load balancer in front of stateless workers if the workload is request-driven, a queue with background workers if bursts need absorbing, a cache in front of repeated model calls if repetition is real, read replicas and connection pooling if a datastore is under read pressure, and sharding only if data volume actually justifies it.

For anything you leave out, say in one line why it does not apply here. Label the diagram as target state.
```

### Extension diagram

```
Draw a Mermaid diagram of where this system goes next, showing today's pipeline as a component inside the larger system. Label it as future state. Then in five sentences, tell me what the first step on that path would be and what it would cost.
```

---

## Understanding prompts (use freely)

These matter most for you. A confused question costs two minutes. A confused answer tomorrow costs the interview.

### I did not follow that

```
I did not follow that. Explain what this stage does and why we built it this way, as if I had not seen the code. Five sentences.
```

### The whole thing again

```
Explain the whole pipeline to me from scratch, five sentences, as if I have never seen it. Then one paragraph on what the model decides versus what our code decides.
```

### Why not the obvious thing

```
Why did we build {{THING}} this way instead of the simplest thing that would work? Five sentences: what the simple version would be, what breaks under it, and what we pay for ours.
```

### Test how much is real engineering

```
If the model returned nonsense for every single record, what would still be correct in our output? Five sentences.
```

### Did not survive reading out loud

```
When I read this out loud it did not make sense to me: {{PASTE}}. Explain it again differently, five sentences, assume I forgot the surrounding context.
```

### What a senior would ask

```
You wrote this stage. If a senior engineer reviewed it in ten minutes, what three questions would they ask? One sentence each, honestly, including where the answer is weak.
```

### Walk the diagram

```
Walk me through the build diagram in docs/01-architecture.md one node at a time. For each node: one sentence on what it does, one on what happens if it fails. Do not exceed two sentences per node.
```

---

## Recovery prompts

### Behind schedule

```
We are behind. Rank what to cut, most expendable first, and tell me what each cut costs us in scoring.
```

### Stuck on the same bug

```
Stop. Describe the system from scratch as if I just walked in, then give me your smallest hypothesis for this failure and the cheapest probe to test it. Do not fix anything until the probe result comes back.
```

### Context lost after a reset

```
Read CLAUDE.md, DOCS-SPEC.md, tasks.md, docs/01-architecture.md and docs/02-decisions.md. Then tell me in five sentences where we are, what the next action is, and anything in the docs that no longer matches the code.
```

### Before a break or sleep

```
Commit and push everything. Then update tasks.md: set Next action to the single specific first thing I should do when I return, and move anything unfinished into Blocked with what unblocks it.
```

### Docs drifted from code

```
Compare docs/01-architecture.md and docs/02-decisions.md against the current state of the code, including the build diagram. List every place the docs say something the code no longer does. Fix the docs, not the code. Show me the diff before writing.
```

---

## Skill commands

```
/ponytail full
```
YAGNI level. Run at session start.

```
/ponytail-review
```
Reviews the current diff for over-engineering, returns a delete list. Run at H16-H20.

```
/ponytail-audit
```
Whole repo rather than the diff. Run once after the review.

```
/config
```
Output style menu. Set to `simple-english:simple-english` if replies get long and bulleted.

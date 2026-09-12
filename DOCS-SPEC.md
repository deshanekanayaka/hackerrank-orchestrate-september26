# DOCS-SPEC — What you write, and when

You (Claude Code) write and maintain every file in `docs/`. I do not fill these in. They are build artifacts and they double as the material I read before the voice interview.

**Nothing here assumes a language, a data format, or a problem domain.** Where a section says "records", "inputs", or "the output artifact", use whatever the problem statement actually specifies.

**Voice**: first person plural. "We chose X because Y." Not "the system implements X."
**Style**: SimpleEnglish rules. Short sentences. No jargon without a few-word definition. No em-dashes. No hedging words.
**Length**: every doc under one screen. If it grows past that, cut the oldest detail rather than adding scroll.
**Diagrams**: Mermaid, so they render on GitHub.

---

## `docs/00-brief.md` — H0-H2, after the input audit

What the system has to do, in language I could repeat to a non-technical friend.

- **The problem in one paragraph**
- **Inputs**: what sources exist, how many records, what the key fields mean, what modalities are present if any beyond text
- **Output**: exact shape the problem statement demands, allowed values per field, expected record count
- **The traps**: every identifier format mismatch, every field name reused with a different meaning, every source that will break a naive loop. One line each.
- **What separates the outcomes**: from any worked examples provided, what actually distinguishes each possible output value. One line each.

Update if the data surprises us later.

---

## `docs/01-architecture.md` — H2-H4, updated whenever the shape changes

How the system works, end to end. This is the most important doc for the interview.

- **Build diagram** — Mermaid flowchart. Every stage as a node, data flow as edges, the model call marked distinctly, each guardrail shown where it sits. Only components that exist in the repo.
- **Pipeline stages** — 5 to 7 stages, one sentence each, in order
- **What the model decides / what code decides / what nobody decides** — three short lists. The third list is the abstain path.
- **Guardrail seams** — table, one row per seam (input validation, output schema validation, allowed-value whitelist, retry, deterministic override, abstain), naming the stage and the file each lives in
- **Why this shape** — two sentences on why this pipeline rather than a single model call
- **What we are deliberately not building** — three items with one-line reasons

The build diagram must match the code. If the code changes shape, the diagram changes in the same loop.

---

## `docs/02-decisions.md` — appended after every REVIEW beat, and after every architectural choice I make

The running log. Newest at the top. Every entry this shape, none longer than seven lines:

```
### D-07 — Confidence on overridden records
**Decision**: cap confidence at 0.3 when a deterministic rule overrode the model.
**Options considered**: recompute confidence from scratch; leave the model value untouched; flat cap.
**Chosen because**: the model's confidence describes its own answer, not ours, so it goes stale the moment we override. Recomputing needs a calibration set we do not have.
**Breaks if**: overrides become the common path rather than the exception.
**Reversal cost**: low, one function.
**Where**: `code/overrides.<ext>`
```

For decisions I made from your options, record that I chose and what you recommended if they differed. The interview may ask why I went against a recommendation, and that is a good story when the reasoning is written down.

---

## `docs/03-trace.md` — H16-H20, after the full run

One real record followed through every stage in words. The judge is likely to ask exactly this.

- **The input record**, real and pasted
- **Per stage**: what it receives, what check runs, what the model is asked and with what context, what is validated on the response, what it produces
- **The final output**, real and pasted
- **Why this record got this answer**, three sentences

Pick a record that exercises at least one guardrail, not the easiest one.

---

## `docs/04-production.md` — H16-H20

How this would run in the real world. Not covered anywhere else and the judge asks it.

Open with the **production diagram**: a Mermaid diagram of the system at scale. This is where the scaling vocabulary belongs. Show, where they genuinely apply: a load balancer in front of stateless workers, a queue absorbing bursts with background workers draining it, a cache in front of repeated model calls, read replicas if there is a datastore under read pressure, connection pooling at the datastore edge, and sharding only if the data volume actually justifies it.

Label the diagram clearly as the target state, not what we shipped. Under it, one line naming what we actually shipped so the gap is explicit and honest.

Then one short answer per question, each in the shape: **direct answer, one concrete detail, the tradeoff, what we would not solve in v1.**

1. **Deployment shape** — batch job, request-response service, or event-driven consumer, and why this problem suits that one
2. **Scale** — what breaks first at 10x and at 100x volume, and which of horizontal scaling, queues, or caching addresses it
3. **Statelessness** — what state the workers hold today, what it would take to make them stateless so they can scale horizontally
4. **Latency** — rough P50 and P99, and the fallback when the tail is slow
5. **Reliability** — what happens when the model API is down, and what degrades rather than fails
6. **Cost** — rough cost per thousand records, and the levers to lower it
7. **Data and privacy** — what leaves the system, what gets logged, what retention looks like
8. **Monitoring** — how we would know output quality degraded a month later, not just that the service is up
9. **Model updates** — how we would change model version without regressing, and what we would test against
10. **Human in the loop** — when a record escalates to a person and what they see
11. **Known failure modes** — three honest ones, what triggers each, how we would detect it in production

Be honest about limits. "We did not test that" scores better than a bluff.

---

## `docs/05-limits.md` — H16-H20, updated until submit

Three to five things that are genuinely fragile, with what we would do about each given another week. No defensiveness, no padding with generic caveats.

---

## `docs/06-future.md` — H16-H20, after the solution works

Where this goes next, as a staged path rather than a wish list. Each stage names what changes, what it unlocks, and roughly what it costs.

Structure it as concrete steps from what we shipped. For example, if we shipped a command line program the path might run: extract the core logic behind a stable interface, wrap that interface in a service, add a thin frontend over the service, then add persistence and background processing. Adapt to what we actually built.

For each step, name:
- **What we add**
- **What it unlocks** for a user
- **What has to change** in the code we already wrote
- **Rough effort**

End with a **Mermaid diagram of the extended system**, clearly labelled as future state, showing how today's pipeline sits inside it. That diagram is a strong interview answer: it shows that today's simple choice was deliberate and has a growth path, rather than being all we could manage.

---

## `docs/07-evaluation.md` — started at H4-H10 when the harness exists, finished at H16-H20

What we measured and what it told us. HackerRank's guidance says the iteration loop matters more than the size of the benchmark, so this doc records the loop.

- **Per-field accuracy** on the labelled examples, as a table. Per field, not one overall number.
- **Iterations**: one row per change we made, with the field targeted, what we changed, and the before and after numbers. Even a change that made things worse belongs here.
- **A strategy we rejected**, with its numbers. Having tried two approaches and measured both is worth more than one approach done well.
- **Cost and latency**: model calls per record, records skipped by cheap gates, estimated cost per full run, wall-clock runtime.
- **What we did not measure** and why.

If the edition ships no labelled examples, say so at the top and describe what we did instead: hand-checked records, consistency checks across similar inputs, or spot audits.

---

## `tasks.md` — repo root, updated at the end of every loop and before every break

Operational, not explanatory, which is why it sits outside `docs/`.

- **Next action** at the top, one specific line: file, function, or command
- **In progress**
- **Blocked**
- **Done**, rolled up rather than a transcript

This file plus `docs/` is how you recover after a `/clear` or session reset. Keep it accurate.

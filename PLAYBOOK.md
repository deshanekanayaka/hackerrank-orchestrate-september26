# PLAYBOOK — Patterns that won previous editions

Drawn from the highest-scoring public submissions to earlier Orchestrate rounds and from HackerRank's own guidance. Every pattern here is stated problem-agnostically. Read this before H2-H4 so you recognise the options when Claude presents them.

The sources span two very different problem shapes: a retrieval and agent task (May, winner out of 12,885) and a vision and verification task (June, winner out of 15,295). Patterns that show up in both are the ones to weight heavily. They are marked **[both editions]** below.

These are not rules. They are priors. If the problem argues against one, say so in `docs/02-decisions.md` and move on — a reasoned departure defends better than a copied pattern.

---

## 0. One agent, one tool  **[both editions]**

The May winner put it bluntly: reach for a multi-agent system only when a dire need forces you to, because a single well-built agent is far more powerful than people give it credit for.

The instinct in a hackathon is to build a router, a specialist per category, and a fistful of tools. It scores worse. It is harder to explain, harder to debug at hour 18, and the boundaries between agents become places where context gets lost.

If you need several capabilities, prefer **one tool with modes** over several tools. The May winner's single tool had three modes: search to find, read to be sure, and an exact-match mode to pin down a literal token that fuzzy matching would lose. That is the same three moves a human makes, and the agent picks per call.

Judges reward clear boundaries, not component count.

---

## 1. Model perceives, code decides  **[June winner, strongly]**

The strongest single pattern. Two independent top submissions landed on it in the same words.

The model is asked only **what it observes**. It never returns the verdict. A deterministic layer takes the model's observations and applies the policy that produces the final answer.

Why it wins: the model cannot hallucinate a decision it was never asked to make. The decision logic becomes readable, testable, and cheap to change. In the interview you can point at a function and say "this is where the answer is decided", which is a far stronger answer than "the model decides".

The tell that you have it right: if the model returned garbage observations, the output would be wrong but never *malformed* or *out of policy*. That is the question worth asking Claude at H2-H4.

---

## 1b. Verify the model's claimed evidence

The single sharpest idea in the May winner. A citation only counted if the agent had **actually opened that source during the turn**. A post-hoc guard checked this, and any answer citing something it never read was downgraded to an escalation.

Generalise it: whenever the model claims its answer rests on some evidence, check mechanically that the evidence was really consulted and really says that. Do not take the citation on trust.

This is cheap to build, catches the most damaging failure mode LLM systems have, and is one of the strongest things you can say in the interview.

---

## 2. Cheap gate before expensive call  **[both editions]**

Put a deterministic check in front of every expensive model call and skip the call when the check already answers.

Examples from winning builds: a regex fast path handled simple inputs and only fell back to the model for ambiguous ones, cutting model calls roughly in half. A cheap library check rejected unusable inputs before any vision call, skipping 20 to 30 percent of them.

The May winner extended it to a **model tier ladder**: deterministic rules handled the trivial inputs, a fast cheap model tagged the easy ones, and the expensive model only woke up for inputs that genuinely needed thinking. Their phrasing was that you should not pay a genius to say "you're welcome".

This costs one function and buys three things: lower spend, faster runs, and a concrete cost story for the interview.

---

## 3. Cache and replay model responses

Save every model response to disk keyed by input. On re-run, replay from disk unless the input changed.

This is the highest-leverage thing you can build in a 24-hour window. It means you can iterate on the deterministic layer as many times as you want without paying for or waiting on the model again. The top submission shipped a replay mode as the default so the whole run reproduced offline with no key at all.

Build it early, with the loader, not late. Retrofitting caching into a pipeline at hour 16 is painful.

---

## 4. Evaluate against the labelled examples from hour four

Editions ship a labelled sample file alongside the unlabelled one. That file is a scoring gift and most participants underuse it.

Build a small harness that runs the pipeline on the labelled set and reports **per-field accuracy**, not just an overall number. Per-field tells you where to spend the next hour. Overall tells you nothing actionable.

Then iterate against it. HackerRank's own guidance says the loop matters more than the size of the benchmark: run, inspect failures, change one thing, run again. A submission that shows three measured iterations beats one that shows a bigger architecture.

The winning repos both shipped an evaluation report as a deliverable, with per-field scores, a comparison of at least two strategies they tried, and a cost analysis.

---

## 5. Deterministic overrides beat model routing

Where a rule can decide, let the rule decide. Reserve the model for genuine judgement.

Common shape: one source of evidence is primary and cannot be overridden by weaker signals. Secondary context can add flags or raise review, but never flip the primary verdict. Encode that as code, not as a sentence in a prompt.

---

## 5b. Abstain loudly, and still give partial value  **[both editions]**

Both winners biased hard toward escalating or abstaining rather than guessing. The May winner's rule: a confident wrong answer is worse than an honest "let me get someone".

The refinement worth copying: when the system abstains, it still surfaces whatever it *can* safely offer before handing off. It did not return an empty shrug; it returned the relevant contact route and the status page, then escalated the rest.

Abstaining is not the same as producing nothing. Give the caller everything you are sure of, then flag the gap.

---

## 6. Be conservative where the schema allows it

Winning calibrations were deliberately timid:

- Cap the most severe value unless evidence is unambiguous
- Treat under-reporting as agreement, not contradiction; reserve contradiction for genuine conflict
- Anchor ambiguous fields to what the input claimed when the evidence merely fails to disprove it
- Default to the abstain value rather than guessing when evidence is missing

Graders reward calibration. Confidently wrong costs more than honestly uncertain.

---

## 7. Detect adversarial inputs before the model sees them

Editions plant inputs designed to derail the model: instructions embedded in the text, instructions embedded inside media, escalation pressure, mixed languages.

Handle each with a deterministic detector that runs **before** the model call, sets a flag, and lets the real task proceed normally. Do not let detection change the verdict. The flag is the output, not a veto.

Have a small table in your docs listing each adversarial category, how you detect it, and what you do. That table is a strong interview artifact and takes ten minutes to write.

---

## 8. Structured output discipline

- Low temperature on every call. Winning builds used around 0.1 for structured JSON.
- Ask for JSON explicitly, state the exact fields, enumerate every allowed value in the prompt.
- Validate the response against a schema object, not by eyeballing keys.
- Normalise the model's vocabulary to your schema with an explicit mapping table. Models return synonyms; a mapping layer turns that from a bug into a non-event.
- One retry on malformed, then abstain. Not infinite retries.

---

## 8b. Make runs reproducible

The May winner used deterministic chunking so the same input produced the same answer on every run. The June winner shipped a replay mode so the whole submission regenerated offline with no key.

Same goal from two directions: a judge should be able to run it twice and get the same thing. Low temperature, fixed seeds on any sampling, deterministic ordering, and cached responses all serve this.

---

## 9. Rate limits and concurrency

Cap concurrent requests with a semaphore. Retry on 429 and 5xx with exponential backoff, three attempts, roughly 2s then 4s then 8s.

Without this a full run dies halfway at the worst possible hour. With it you get a concrete reliability answer for the interview.

---

## 10. Targeted recovery, not full restart

When a consistency check fails, re-run the single stage that produced the bad value. Do not restart the pipeline.

Name the consistency rules explicitly. One winning build had seven named rules and re-ran individual components on failure. That is both better engineering and a better story than a blanket retry.

---

## 11. Ship an honesty note

The top submission included a short section in its README explaining exactly how the output was produced, what was cached versus live, and confirming nothing was hardcoded to the labels.

It costs five lines and it pre-empts the judge's most awkward question.

---

## 12. Cost and latency table

A small table showing calls per record, records skipped by cheap gates, estimated cost per run, and wall-clock runtime.

This is the single fastest way to look like an engineer rather than a hackathon participant, and it gives you real numbers for the production questions in the interview.

---

## 13. Read the scoring rubric if one ships

The May repo included an `evaluation_criteria.md` alongside the problem statement (spelled `evalutation_criteria.md` in that edition, so search rather than assume the filename).

If tomorrow's edition ships one, it is the literal rubric you are scored against. Read it at H0 with the problem statement, and have Claude cross-check the architecture against it at H2-H4. Surprisingly many participants never open it.

---

## What this implies for tomorrow

The build order that falls out of the above:

1. Loader and input validation
2. **Response cache and replay** — before any real model calls, and it makes runs reproducible
3. Prompt layer with enumerated allowed values
4. One model call returning observations only
5. Deterministic decision layer
6. **Evaluation harness against the labelled set** — then iterate
7. Guardrails: schema validation, value whitelist, retry, overrides, abstain
8. Evidence verification, if the output claims to rest on specific sources
9. Adversarial detectors
10. Concurrency and backoff

Items 2 and 6 are the ones most participants skip and the ones that pay back most inside a 24-hour window. Item 8 is the one that separates a careful submission from a fluent one.

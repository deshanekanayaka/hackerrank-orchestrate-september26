# DAY-OF — What you do tomorrow

**Part 1 (tonight) is done.** Skills installed, output style verified, key ready.

What follows is H0 onwards. Claude Code drives the build. You decide the architecture from options it presents and stay engaged through each loop.

**Nothing here assumes the problem.** It could be text, images, audio, structured records, or a mix. Every prompt works either way, because the problem statement supplies the specifics.

---

## H0 — Setup (5 minutes)

### 1. Put the hackathon material in this folder

The starter is already unzipped here. The hackathon material goes in beside it, not in a subfolder.

Cloning:

```
git clone --depth 1 https://github.com/interviewstreet/hackerrank-orchestrate-<edition>.git tmp
mv tmp/* tmp/.[!.]* . 2>/dev/null; rm -rf tmp
```

Or unzip their zip here, or drag the contents in.

When it is right, `ls` shows their files and yours side by side:

```
AGENTS.md  CLAUDE.md  problem_statement.md  code/  dataset/
DAY-OF.md  PROMPTS.md  DOCS-SPEC.md  CLAUDE.orchestrate.md  docs/  tasks.md  setup.sh
```

If their material landed in a subfolder, move it up before continuing. The rest of the day assumes `dataset/` and `code/` are at this level.

### 2. Run setup

```
bash setup.sh
```

Merges the operating agreement into their `CLAUDE.md`, creates `.env` and `cache/`, updates the ignore list, asks for your H0 time. Safe to run twice.

### 3. API key

Paste it into `.env`.

### 4. Skim the merged CLAUDE.md

Thirty seconds. The starter rules are between the `orchestrate-starter` markers at the bottom. If anything there contradicts the platform's rules above it, delete the starter line. Theirs wins.

### 5. Open and verify

```
code .
```

Split the terminal: one pane for `claude`, one for running things. In the Claude pane:

```
claude
```

```
/ponytail
```

Should report `full`. If not, `/ponytail full`.

---

## H0 to H2 — Understand

**First 20 minutes, alone.** Read the problem statement twice. Read `AGENTS.md`.

**Also look for a scoring rubric file.** Previous editions shipped one next to the problem statement, sometimes misspelled (`evalutation_criteria.md` in May). Run `ls *.md` and open anything that looks like criteria. It is the literal rubric you are scored against and many participants never open it.

This is the only solo block and it is worth it: you will catch things in Claude's audit that you would otherwise take on trust.

**Then paste:**

```
Read the problem statement and inventory every input the challenge provides. Do not write pipeline code and do not propose an architecture yet.

Audit the inputs: what sources exist, how many records, the structure and types of each, missing values, the key fields and their formats, and the relationships between sources. Then tell me every identifier format mismatch that would break a naive join, every field name reused with a different meaning across sources, any non-text modality present and what handling it needs, and anything that would break a naive per-record loop.

Also check whether this edition ships a scoring rubric or evaluation criteria file alongside the problem statement. If it does, read it and summarise how we are scored as a section in docs/00-brief.md.

Then write docs/00-brief.md following DOCS-SPEC.md.

Then stop. Tell me in five sentences what this problem actually is and what the three worst traps are.
```

**You do**: read `docs/00-brief.md`. If a trap does not make sense, ask about that one. Do not move on with a fuzzy picture of the data.

**Move on when**: you could say what goes in and what comes out.

---

## H2 to H4 — Architecture (you decide)

Your phase. Claude proposes, you choose.

**Read `PLAYBOOK.md` first**, ten minutes, while Claude is still working on the brief. It lists the patterns that scored well in earlier editions so you recognise the options rather than meeting them cold.

**Paste:**

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

Read them. Choose. Mix and match freely, and pick against a recommendation if you understand the trade.

**Then paste:**

```
Here are my choices: {{list them, one line each}}.

Now write docs/01-architecture.md following DOCS-SPEC.md. Include the Mermaid build diagram showing every stage, the data flow, where the model is called, and where each of the six guardrails sits. Only put components in the diagram that will actually exist in the repo.

Then open docs/02-decisions.md with one entry per decision above, recording what I chose, what you recommended, and why.

Then stop and walk me through the architecture in five sentences.
```

**You do**: read `docs/01-architecture.md`, especially the build diagram and the "what the model decides versus what code decides" section. That section is the spine of everything you say tomorrow.

One question worth asking whatever the answer:

```
If the model returned nonsense for every single record, what would still be correct in our output? Five sentences.
```

The answer tells you how much of this is real engineering versus a prompt wrapper, and it is a strong thing to be able to say out loud.

**Move on when**: you can name the stages in order while pointing at the diagram.

---

## H4 to H10 — Build

**Paste once:**

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

Then for each next stage: `go`.

**Rhythm per stage**: read the PLAN, say go, watch the TEST output, read the REVIEW, say next.

**After stage 6, the harness exists. Switch to measured iteration:**

```
Run the evaluation harness and show me per-field accuracy. Then tell me which single field has the most room to improve and what one change would move it. Do not make the change yet.
```

Make one change, re-run the harness, keep it if the number moved. Log each iteration in `docs/02-decisions.md` with the before and after numbers. Three measured iterations beat one bigger architecture, and the numbers are excellent interview material.

**Break 10 minutes every 90 minutes.** Away from the screen.

**When a REVIEW does not land:**

```
I did not follow that. Explain what this stage does and why we built it this way, as if I had not seen the code. Five sentences.
```

**Move on when**: the pipeline runs end to end, the cache works, and the harness reports real per-field numbers.

**Before sleep:**

```
Commit to a stage branch and request approval before merging and pushing to main (CLAUDE.md Hard Rule 8). Then update tasks.md: set Next action to the single specific first thing I should do when I wake, and move anything unfinished into Blocked with what unblocks it.
```

---

## H10 to H16 — Sleep

Six hours. Two alarms, phone across the room. The harden phase after this is where submissions separate from prototypes and it needs a working brain.

---

## H16 to H20 — Harden

Coffee first. Read `docs/01-architecture.md` and `docs/02-decisions.md` before touching anything.

**Paste:**

```
Run the pipeline on the full input set. Then review the output like a reviewer who has never seen this project.

Show me: record count against input count, any duplicate keys, any value outside the allowed set, any out-of-range numbers, any required field left empty. Then sample 20 records, 10 routine and 10 that look wrong, and for each of the wrong-looking ones tell me what the input was, what we produced, and whether it is actually correct.

Then audit the code for missing guardrails against the six seams in docs/01-architecture.md.

Report everything. Fix nothing yet.
```

**You do**: pick what to fix. Unsure? Ask which three matter most and why. Then let Claude fix them one loop at a time.

**Then:**

```
/ponytail-review
```

```
/ponytail-audit
```

Delete what it flags unless there is a reason to keep it.

**Then the remaining docs:**

```
Write docs/03-trace.md, docs/04-production.md, docs/05-limits.md, docs/06-future.md and docs/07-evaluation.md following DOCS-SPEC.md.

For the trace, pick a real record that exercises at least one guardrail, not the easiest one.

For production, open with the Mermaid production diagram at scale. Use load balancing, stateless workers, queues with background workers, caching, read replicas, connection pooling and sharding only where they genuinely apply to this problem. Label it clearly as target state and say in one line underneath what we actually shipped.

For future, give me a staged extension path from what we built, each stage naming what we add, what it unlocks, what has to change in existing code, and rough effort. End with a Mermaid diagram of the extended system showing where today's pipeline sits inside it.

For evaluation, report per-field accuracy on the labelled set, the iterations we ran with before and after numbers, at least one strategy we tried and rejected with its numbers, and the cost and latency table.

Be honest in limits. Do not pad with generic caveats.
```

**Adversarial check.** Editions plant inputs designed to derail the model:

```
Check how the pipeline handles adversarial inputs: instructions embedded in text, instructions embedded in media if this problem has media, escalation or pressure language, and mixed languages. For each, tell me whether we detect it, whether detection happens before the model call, and whether it changes the verdict when it should only raise a flag. Report first, fix after I confirm.
```

**Move on when**: full run is clean, counts match, all values in their allowed sets, and the eval numbers are recorded.

---

## H20 to H21 — Read

No new code. Sixty minutes.

Read in this order: `docs/01-architecture.md`, `docs/03-trace.md`, `docs/02-decisions.md`, `docs/04-production.md`, `docs/06-future.md`, `docs/05-limits.md`.

**Read the architecture doc and the trace out loud.** Once each, at speaking pace. Twenty minutes of the sixty. That is the whole rehearsal, and it matters because the interview is voice: reading silently and speaking are different skills.

Anything you stumble over is something you do not yet understand:

```
When I read this out loud it did not make sense to me: {{paste the bit}}. Explain it again differently, five sentences, assume I forgot the surrounding context.
```

If something is wrong rather than unclear, there is still time. That is why this hour sits before submit.

---

## H21 to H23 — Ship

**Paste:**

```
Final submission pass. Open the output artifact as if you had never seen this project, and check it against the problem statement exactly: field names and order, one record per input record, no duplicate keys, every value within its allowed set, every number in range, and any explanation field actually explaining rather than padding.

Then rewrite the README at repo root so a judge can clone this and run it in five minutes: setup steps, runtime version, dependencies, environment variables, the single run command, and what the program reads and writes. Include the build diagram from docs/01-architecture.md, the per-field evaluation numbers, and the cost and latency table.

Add a short honesty note near the end explaining exactly how the submitted output was produced: what was live, what was replayed from cache, and confirming nothing is hardcoded to the labelled examples.

Report issues first. Fix them one at a time after I confirm.
```

Before zipping, check the starter files are not confusing the submission. `DAY-OF.md`, `PROMPTS.md`, `DOCS-SPEC.md`, `CLAUDE.orchestrate.md` and `setup.sh` are yours, not deliverables. `docs/` is worth including: it is the build story and it helps the code score.

```
The starter workflow files (DAY-OF.md, PROMPTS.md, DOCS-SPEC.md, CLAUDE.orchestrate.md, setup.sh) are my personal process, not part of the submission. Move them into a workflow/ folder so the repo root shows only the solution, its docs, and the hackathon files. Do not move docs/ - that is part of the submission.
```

Zip and submit. **Target H23.** The spare hour changes how the last two feel.

---

## H23 to H24 — Buffer

Nothing broken? Water, food, walk. Then read `docs/03-trace.md` and `docs/04-production.md` once more, out loud.

---

## If things go wrong

**Behind schedule at H8**

```
We are behind. Rank what to cut, most expendable first, and tell me what each cut costs us in scoring.
```

**Same bug for 20+ minutes**

```
Stop. Describe the system from scratch as if I just walked in, then give me your smallest hypothesis for this failure and the cheapest probe to test it. Do not fix anything until the probe result comes back.
```

**Sleep window collapsed** — sleep at least four hours. Cut from harden, not from sleep.

**Lost the thread at H16**

```
Explain the whole pipeline to me from scratch, five sentences, as if I have never seen it. Then one paragraph on what the model decides versus what our code decides.
```

Twenty minutes here beats four hours of editing code you do not understand.

**Setup went wrong and files are in the wrong place**

```
Look at the current directory structure and tell me what is misplaced relative to what the problem statement expects. Then give me the exact commands to fix it. Do not run them.
```

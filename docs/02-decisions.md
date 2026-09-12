# 02 — Decision Log

Newest first. One entry per architectural choice. Seven lines maximum per entry.

---

### Stage 4: Model call layer implementation choices

**Decision**: `strip_fences` lives in `prompts.py` and is imported by both `ocr.py` and `parse_messages.py`, avoiding duplication.
**Rejected**: separate file (one more name to track for a 6-line function).
**Risk**: synchronous calls. A rate-limit error kills the run until Stage 10 adds backoff.
**Note**: image failure sets `evidence_complete[user_id] = False`. Message failure logs and skips (not fatal).
**Where**: `code/ocr.py`, `code/parse_messages.py`, `code/prompts.py`

---

### Stage 3: Prompt layer implementation choices

**Decision**: prompt strings and response dataclasses live together in `code/prompts.py`. Every allowed intent value is listed verbatim in the prompt text.
**Rejected**: pydantic models (not installed, adds a new dependency). Inline dict key checks in Stage 4 (ad-hoc, not reusable).
**Risk**: `new_date` format is not regex-validated. `forecast.py` will coerce a bad date to None rather than reject the whole message result.
**Where**: `code/prompts.py`

---

### Stage 2: Cache implementation choices

**Decision**: one JSON file per cache entry, named by SHA-256 hex digest of the key string, stored in `cache/`.
**Rejected**: SQLite (adds a connection/lock layer for a single-writer workload), in-memory dict (lost on every run, defeating the replay purpose).
**Risk**: a corrupt JSON file raises on `get`. The Stage 4 caller treats any exception as a miss and re-calls the model.
**No TTL, no LRU**: the 24-hour run window makes expiry irrelevant. Entries are write-once per unique key.
**Where**: `code/cache.py`

---

### Stage 1: Loader implementation choices

**Decision**: load all CSVs to string dtype first, then cast numerics and dates with `errors="coerce"`.
**Rejected**: strict dtype inference at read time. Pandas inference silently promotes integer columns containing blanks to float, and it rejects mixed-format date strings rather than leaving NaN.
**Risk**: a malformed amount becomes NaN instead of a crash. The Stage 7 guardrail will catch NaN in critical fields before any decision row is written.
**Where**: `code/load_inputs.py`

---

### D-10: Evidence verification

**Decision**: generate `decision_explanation` from code using actual event IDs, never from a model prompt.
**Options considered**: (A) post-hoc citation whitelist, (B) full provenance trace per output field, (C) code-generated explanation only.
**Chosen because**: if the model never writes the explanation, a hallucinated citation cannot exist. No whitelist guard is needed.
**Breaks if**: the scoring rubric rewards rich natural-language explanation that requires the model. We can check this against sample_requests.csv.
**Reversal cost**: medium. Requires a model call for explanation and a new whitelist guard.
**Where**: `code/decide.py`

---

### D-09: Model tiering

**Decision**: no model tier ladder. The architecture already limits model calls to 16 images and up to 215 messages total.
**Options considered**: (A) deterministic pre-filter for trivially affordable records, (B) two model tiers for messages vs images, (C) no tiering.
**Chosen because**: the cheap-gate principle from the PLAYBOOK is already met by pre-processing. Model calls are per-user, not per-record.
**Breaks if**: profiling shows the balance forecast is slow and a fast path saves meaningful time.
**Reversal cost**: low. Add a pre-filter check in `forecast.py`.
**Where**: `code/forecast.py`

---

### D-08: Evaluation

**Decision**: per-field exact-match accuracy against sample_requests.csv, run after every code change.
**Options considered**: (A) overall accuracy only, (B) per-field accuracy, (C) weighted score matching rubric weights.
**Chosen because**: per-field accuracy tells us which field to fix next. Overall accuracy is not actionable.
**Breaks if**: nothing. This decision has no downside.
**Reversal cost**: not applicable.
**Where**: `code/evaluate.py`

---

### D-07: Abstain policy

**Decision**: three hard triggers cap `affordability_status` at `not_affordable` with `amount_safe_to_pay = 0`.
**Options considered**: (A) binary evidence flag capping to not_affordable, (B) soft abstain degrading to affordable_later, (C) no abstain with zero as default.
**Chosen because**: the PLAYBOOK says to be conservative where the schema allows it. Option C risks wrong positive labels, which cost more than abstentions.
**Breaks if**: the scoring rubric penalises not_affordable more than affordable_later for incomplete evidence.
**Reversal cost**: low. Change the cap target in `decide.py`.
**Where**: `code/decide.py`

---

### D-06: Non-text inputs

**Decision**: Claude Haiku vision call per image, result cached by image_id and file hash.
**Options considered**: (A) Claude Haiku vision API, (B) Tesseract local OCR, (C) GPT-4o vision.
**Chosen because**: 16 calls total, result cached, same SDK already in use. Tesseract struggles with stylized receipt fonts.
**Breaks if**: the contest environment has no outbound internet.
**Reversal cost**: medium. Swap the model call for a Tesseract subprocess in `load_inputs.py`.
**Where**: `code/load_inputs.py`

---

### D-05: Confidence

**Decision**: binary `evidence_complete` flag per user. False forces not_affordable across all that user's requests.
**Options considered**: (A) binary evidence flag, (B) probability score from the model, (C) field-level evidence flags.
**Chosen because**: a single binary flag stops a missing image amount from producing a wrong affordable_now verdict.
**Breaks if**: per-field granularity turns out to matter for scoring. We can observe this from sample_requests.csv.
**Reversal cost**: low. Add per-field flags in `load_inputs.py`.
**Where**: `code/load_inputs.py`

---

### D-04: Retrieval

**Decision**: no retrieval layer. Join on declared foreign keys only.
**Options considered**: (A) no retrieval, (B) keyword search over messages, (C) embeddings over messages.
**Chosen because**: every relationship is encoded as a foreign key. Retrieval solves a problem this dataset does not have. Departure from PLAYBOOK retrieval option recorded here.
**Breaks if**: nothing in this problem.
**Reversal cost**: not applicable.
**Where**: `code/load_inputs.py`

---

### D-03: Routing

**Decision**: fully deterministic routing everywhere. The model never decides which code branch runs.
**Options considered**: (A) fully deterministic routing, (B) model classifier per request type, (C) heuristic pre-filter for obvious cases.
**Chosen because**: every branch in the decision layer is a rule over numbers. No ambiguous class requires a model to name it.
**Breaks if**: affordability categories develop overlapping numeric conditions that require qualitative weighting.
**Reversal cost**: medium. Add a classifier call and a routing layer.
**Where**: `code/decide.py`

---

### D-02: Model calls per record

**Decision**: zero model calls per request record. All model work runs once in Stage 1.
**Options considered**: (A) zero per-record calls with pre-processing only, (B) one structured-output call per record, (C) two calls per record.
**Chosen because**: images and messages are user-level data, not request-level. Pre-processing them once means 250 decisions run at zero marginal model cost.
**Breaks if**: a future edition has per-request evidence unique to each record.
**Reversal cost**: medium. Add a per-record model call in `decide.py`.
**Where**: `code/load_inputs.py`

---

### D-01: Pipeline shape

**Decision**: three stages (load_inputs.py, forecast.py, decide.py) plus write_output.py.
**Options considered**: (A) three stages, (B) five stages separating OCR and message parse, (C) one stage per record.
**Chosen because**: three stages map to three kinds of work. Cache keys sit at the stage boundary. Five stages add granularity at the cost of extra handoff points.
**Breaks if**: message parse errors are hard to isolate without a dedicated stage.
**Reversal cost**: low. Split Stage 1 into load_inputs.py and parse_messages.py.
**Where**: `code/`

---

### D-00: Division of labour

**Decision**: the model perceives (image amounts, message intent). Deterministic code decides all eight output fields.
**Options considered**: (A) model decides all 8 fields, (B) model observes only, code decides, (C) model decides ambiguous records only.
**Chosen because**: the PLAYBOOK's strongest-weighted pattern. The decision layer is testable and auditable without any model calls.
**Breaks if**: the balance forecast itself requires judgement calls that code cannot encode.
**Reversal cost**: high. Requires prompt engineering for all output fields and new guardrails.
**Where**: `code/decide.py`

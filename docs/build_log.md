# MomoParse — Build Log

A running, plain-language record of every non-trivial change. Each entry is written so you can re-read it after time away and re-explain what the system does — for the paper, for a pitch, or for your own maintenance.

Entries are **reverse chronological** (newest first). Each entry follows:

- **What changed** — files + one-line summary
- **Why it matters** — the paper/pitch framing
- **How it works** — the mechanism in plain terms
- **How to verify** — the test or command that proves it

Companion docs: [improvements.md](improvements.md), [research_paper_structure.md](research_paper_structure.md), [ml_benchmark.md](ml_benchmark.md).

---

## 2026-04-23 — End-to-end demo surfaces + fixes four real parser bugs

**What changed**
- [scripts/demo_report.py](../scripts/demo_report.py) — new end-to-end script: reads an XML SMS export, runs the full pipeline (parser → categorizer → enricher), and prints a plain-English Financial Health Report with score, driver breakdown, cash flow, category split, monthly timeline, insights, and recommendations. The script applies two corrections the standard API path omits because it doesn't know about the XML envelope: attaches the XML's Android-export timestamp as a date fallback when the parser can't recover a date from the SMS body, and dedupes by transaction_id so paired MTN-branded + MoMo-branded SMS don't double-count.
- [parser/pipeline.py](../parser/pipeline.py) — new `_is_failure_notice()` pre-check at the top of `parse()`. Rejects two classes of SMS that look transaction-shaped but should not be counted: **failures** (daily-limit exceeded, failed to send, insufficient funds, voucher expired and returned) and **notification-only duplicates** (MoMo's low-info "Deposit made to your bank account number: ****XXXX..." confirmation that arrives paired with the rich "Your payment of GHS X to <bank> has been completed..." record for the same tx_id). Returns `match_mode=none` for both.
- [parser/matcher.py](../parser/matcher.py) — fuzzy matching now requires a tx-type-specific *product noun* to be present in the SMS before accepting a template (airtime → "airtime"; bundle → "bundle"; loan → "loan"; interest → "interest"). Prevents the mtn_airtime_purchase template from being fuzzy-matched against generic "payment to <merchant>" SMS on token-overlap alone, which was inflating airtime totals by ~GHS 880k in the demo report. Verbs (withdrawn, deposit, etc.) are not gated because the drift benchmark specifically mutates them.
- [parser/matcher.py](../parser/matcher.py) — `_field_capture_score` now treats a template's explicit `null` critical field as "structurally absent," dropping it out of the confidence denominator instead of counting as a miss. Lets templates that truthfully can't carry a field (e.g. MTN's Money-Transfer-Deposit SMS has no balance) score full confidence on what they can carry.
- [configs/mtn_templates.json](../configs/mtn_templates.json) — new `mtn_money_transfer_deposit` template for the cross-bank deposit format (`"Money Transfer Deposit received for GHS X from <NAME> Token: <digits> Transaction ID: <digits>..."`) previously falling through to weak fuzzy matches.
- [scripts/import_sms_xml.py](../scripts/import_sms_xml.py) + [scripts/demo_report.py](../scripts/demo_report.py) — added **T-CASH** to the allowed sender whitelist. Its absence had silently dropped every Telecel message in the previous import (1,175 messages from this export alone); the fix added 1,079 new Telecel rows to the corpus on re-import.
- [tests/test_corpus_real.py](../tests/test_corpus_real.py) — skips (i) rows whose body contains `name_<hex>` / `ph_<hex>` PII-hash tokens (template regexes expect raw digits/caps; hashing is an artifact of our corpus-scrubbing pipeline, not a parser regression), and (ii) rows correctly identified as failure/duplicate-notification.
- [corpus/real_sms_corpus.csv](../corpus/real_sms_corpus.csv) — re-imported against the fixed parser. Grew from 994 → 2,073 rows; telco distribution is now roughly balanced between MTN (956) and Telecel (1,117).
- [docs/demo_report.md](demo_report.md) — regenerated end-to-end against the fixed pipeline.

**Why it matters**

Running the tool against your friend's real 2,724-message export was the first time the full pipeline was exercised on an SMS corpus it did not synthesize. It worked — and produced numbers that were wrong in ways the synthetic test fixtures could never have revealed. This entry is the round-trip of *run it on real data → believe the numbers less than the numbers deserve → find the bugs → fix them → get a reading you'd actually stand behind in front of a lender.*

Four bugs, all real, all shipping fixes:

1. **Failed transactions counted as real.** A single "daily transaction limit exceeded... failed to send GHS 10,000" notice was adding GHS 10,000 to category totals. Across 3.5 years of data this inflated several categories; on short windows it was enough to flip the sign of the monthly savings rate.
2. **Fuzzy matching hallucinating airtime purchases.** Any MTN "Your payment of GHS X to <MERCHANT> has been completed at..." SMS — of which there were hundreds, for real merchants like VODAFONE PUSH and bank cashouts to Ecobank — was being fuzzy-matched to the airtime_purchase template because that template's boilerplate shares 20+ tokens with the SMS and its example is shorter, so the Jaccard score is higher. The template's `counterparty_name: "literal:MTN AIRTIME"` then hard-coded the counterparty, and the categorizer dutifully put ~GHS 880k into airtime over 3.5 years. Requiring the product noun "airtime" to appear in the SMS before the airtime template can fuzzy-match eliminates the false positives while preserving drift tolerance for verb swaps (which the drift benchmark tests).
3. **Duplicate notifications beating real transactions in dedup.** MoMo sends two SMS for cash-outs to bank: a no-amount "Deposit made to your bank account number: ****XXXX..." and the rich "Your payment of GHS X to <bank> has been completed..." Both carry the same tx_id. Because the thin one arrived first in the XML, the importer's dedup kept it and discarded the rich one — silently throwing away the amount. Treating the thin notification as non-transactional lets the real record win dedup.
4. **T-CASH not in the sender whitelist.** The whitelist used "Telecel" and "VodafoneCash" but not the actual handset shortcode "T-CASH" that the rest of the project already uses in test fixtures. 1,175 Telecel messages were dropped on the first import — catching this doubled the real corpus.

The score moving from 57 → 27 on the same data is the point of this work, not a regression. 57 was a number built on counted-but-failed transactions, doubled tx_ids, and hallucinated airtime purchases. 27 is the honest reading of a MoMo account that sees a lot of throughput but does not net-save. A lender who asked for the first number would have been misled; the second number is a decision they can act on.

**How it works**

*Failure + notification filter.* A compiled regex fires at the top of `MoMoParser.parse()` against the SMS body. Two regex groups: `_FAILURE_MARKERS` (failed to send, exceeded daily limit, transaction declined/rejected/reversed, voucher expired and returned, has failed at, insufficient funds, could not be completed) and `_NOTIFICATION_ONLY` (opens with "Deposit made to your bank account number"). A hit on either returns `ParseResult(match_mode="none", telco="unknown")` — downstream aggregation drops these rows and the dedup path lets paired real transactions win.

*Fuzzy signal gating.* Before `fuzzy_match()` runs, `TemplateMatcher` filters the candidate template list with `_tx_type_signal_present()`. Templates whose tx_type is in the `_TX_TYPE_SIGNALS` dict require a keyword in the SMS to remain eligible; tx_types not in the dict are unrestricted. The gated tx_types are product-noun-bearing ones (airtime, bundle, loan, interest) that telcos do not rewrite across template revisions — keeping them out of the drift mutation space preserves the drift benchmark's guarantees. Verbs that do drift (withdrawn → removed, paid → remitted) are deliberately not gated.

*Null-as-absent field scoring.* `_field_capture_score` previously treated a template field whose rule was `null` in the JSON the same as a failed group extraction — both scored 0 for that field. That forced templates to score low even when they honestly don't carry a particular field (the Money-Transfer-Deposit SMS has no balance in the body). The updated logic drops `null` fields out of the applicable-fields denominator: a template that captures amount + counterparty + tx_id and declares balance `null` scores 1.0 instead of 0.71.

*Demo script end-to-end.* `scripts/demo_report.py` loads the XML, filters to allowed senders, parses + categorizes each SMS (with XML-timestamp date fallback and tx_id dedup), calls `enricher.analytics.compute_report`, and renders a plain-English report. No API server needed; direct in-process calls to the same functions the `/v1/report` endpoint uses.

**How to verify**

```bash
# End-to-end: full history or last N months
python scripts/demo_report.py "<path-to-xml>" --write docs/demo_report.md
python scripts/demo_report.py "<path-to-xml>" --months 6

# Re-run on fixed parser (assumes T-CASH fix already merged)
python scripts/import_sms_xml.py import "<path-to-xml>" --dry-run

# Confirm tests still green
python -m pytest tests/test_drift.py tests/test_fuzzy.py tests/test_telemetry.py tests/test_corpus_real.py -q
```

Corpus now: **2,073 rows real** (956 MTN + 1,117 Telecel). End-to-end demo numbers on the full export:

| Metric | Before fixes | After fixes |
|---|---|---|
| Unique transactions | 906 | 2,020 |
| Financial Health Score | 57 | 27 |
| Airtime (top-category slot) | GHS 880k false | removed |
| Net cash flow | −GHS 1.04M | −GHS 79k |
| Monthly income (sample) | flat GHS 26,866 | GHS 994–3,822 |

**Paper framing (section — Validation on real data)**

> We exercised the full pipeline (parser → categorizer → enricher → score) end-to-end against a consented 2,724-message SMS export from a third-party user. Doing so surfaced four classes of parser defect invisible on synthetic fixtures: (i) failed and reversed transactions being counted as executed — the pipeline now rejects them at the parser stage via an explicit failure-marker filter; (ii) fuzzy template matching assigning product-bearing tx_types (airtime, bundle) to generic merchant SMS on token-overlap alone — mitigated by requiring a tx-type-specific product noun in the SMS for these templates; (iii) paired duplicate-notification SMS winning the importer's tx_id dedup against the richer record for the same transaction — fixed by classifying the low-info notification as non-transactional at the parser stage; and (iv) a misconfigured sender whitelist that silently excluded an entire telco (Telecel, shortcode T-CASH) from the corpus. Each fix was validated both by the existing drift benchmark (no regressions) and by re-running the end-to-end demo, which moved the user's composite Financial Health Score from 57/100 (an artefact of the above bugs) to 27/100 (an honest reading). The exercise is a concrete instance of the alt-credit-scoring literature's general point — synthetic data does not surface the failure modes that matter for deployment — and gives the paper a reproducible before/after on a single anonymised real-user account.

---

## 2026-04-23 — Real-SMS corpus expansion + discovered evaluation closed-loop

**What changed**
- [scripts/import_sms_xml.py](../scripts/import_sms_xml.py) — new importer with two subcommands: `import` (consume an Android SMS Backup & Restore XML file, parse each message, hash personal identifiers, append to `corpus/real_sms_corpus.csv`) and `redact-existing` (retroactively hash PII in rows already in the corpus so the full file uses one convention).
- [corpus/real_sms_corpus.csv](../corpus/real_sms_corpus.csv) — grew from **91 → 994 rows** (+903 real MTN MoMo transactions from a consented third-party XML export). All counterparty names replaced with `name_<10hex>`, all phone numbers with `ph_<10hex>`, balances redacted. The file is gitignored (verified at [.gitignore:56](../.gitignore#L56)); PII never enters git history.
- [categorizer/label_corpus.py](../categorizer/label_corpus.py) — emits a new `source` column (`real` / `synthetic`) so downstream evaluation can stratify on provenance.
- [scripts/evaluate.py](../scripts/evaluate.py) — reads the `source` column and adds a new "Real-only held-out" section: trains on `synthetic + real_train`, evaluates on a held-out slice of real rows only. A new "Known evaluation limitation" section honestly documents why even this evaluation is not a generalization metric.
- [docs/ml_evaluation.md](ml_evaluation.md) — regenerated against the expanded corpus.

**Why it matters**

Two wins and one honest finding, in the order they happened.

First, **real data matters for the paper.** A categorizer trained only on synthetic template-generated SMS is easy to dismiss as a toy. Getting 903 real MTN messages — from a different user, across ~2.5 years of activity, covering marketing filtering, template drift in the wild, and the messy reality of MoMo confirmations that come in pairs — is the first time the system has been exposed to data it did not generate itself. That is the material difference between "works on my test fixtures" and "works on a phone that existed before this project did."

Second, **we committed in code to the data-minimization claim** the paper needs. The [data minimization audit](data_minimization.md) written yesterday asserts raw SMS never persists. The importer now enforces the same posture for training data — third-party names and phones are hashed at import time, and existing rows were retroactively updated so the full corpus is consistent. The audit's paper paragraph about "user-owned" data is now defensible in the training-set context too, not just the runtime context.

Third, **running the new evaluation pipeline surfaced a real methodological issue** and the honest response was to document it, not paper over it. `label_corpus.py::_label()` assigns categories by inspecting `tx_type + keywords on reference/counterparty`; `features.py` one-hot-encodes `tx_type` and flags the same keywords on the same text. Labels and features are therefore near-isomorphic functions of the same raw signals. Any classifier will score near-perfectly — including on a real-only held-out slice — not because it generalizes, but because the task is effectively an identity map between rule-derived labels and rule-derived features. Recognising this in `docs/ml_evaluation.md` and pointing at the existing item #20 in `docs/improvements.md` (human-labeled ground truth + inter-annotator agreement) is the paper-honest next step. It is a known limitation written down, not a claim silently inflated.

**How it works**

*Import path.* Android SMS Backup & Restore exports XML with one `<sms>` element per message (address, body, date, etc.). The importer iterates, filters on a whitelist of MoMo sender IDs (`MobileMoney`, `MTN`, `Telecel`, `VodafoneCash`, `Vodafone`), runs each body through the project's own parser (`parser.parse(body, sender_id=address)`), and discards `match_mode == none` — that dumps marketing and unknown templates. For each parsed transaction it hashes the extracted counterparty name and phone (SHA-256 → first 10 hex chars, prefixed `name_` / `ph_`), replaces those exact strings in the body, sweeps any remaining Ghana-format phone pattern with the same hash scheme, and redacts `(Current|Available|New|Your new) Balance: GHS X,XXX.XX` to `Balance: GHS [redacted]`. Dedup is by transaction ID against the existing corpus. The same hashing applies to the `counterparty_name`, `counterparty_phone`, and `reference` columns so the CSV row and the body stay in agreement.

*Retroactive redaction.* The `redact-existing` subcommand walks the rows already in the corpus, reads each row's (name, phone), and applies the same redaction pipeline. Rows already in hashed form (name starting `name_`, phone starting `ph_`) are skipped so the operation is idempotent.

*Provenance tagging.* `label_corpus.py` now iterates over a list of `(path, source)` pairs instead of bare paths, writing the tag into a new `source` column. `scripts/evaluate.py::_load_labeled()` reads the tag; `_real_only_holdout()` stratifies the real rows 80/20, trains on `synthetic + real_train`, and scores on `real_test`.

*Honest limitation write-up.* The evaluation report now has a "Known evaluation limitation" section stating in plain terms that near-perfect F1 is expected under the current labeling scheme, what a paper-honest evaluation would require (human-labeled ground truth + inter-annotator agreement), and what this evaluation does tell us (internal consistency of the labeling rules, operational floor guarantee, and baseline separation on the original 406-sample set).

**How to verify**

```bash
# Inspect what would change before running for real
python scripts/import_sms_xml.py redact-existing --dry-run
python scripts/import_sms_xml.py import "<path-to-xml>" --dry-run

# Actual run
python scripts/import_sms_xml.py redact-existing
python scripts/import_sms_xml.py import "<path-to-xml>"

# Regenerate labels + evaluate
rm categorizer/labeled_data.csv
python -m categorizer.label_corpus
python scripts/evaluate.py --write-md
```

Current snapshot after import (seed 42):

- Corpus: **994 real rows** + 7,600 synthetic → **7,194 labeled** rows after skipping rows with blank `tx_type`.
- Full-corpus CV weighted F1: **1.000 ± 0.000** (RF / LogReg), **0.995 ± 0.001** (NB), **0.224 ± 0.001** (majority class).
- Real-only held-out weighted F1: **1.000**.
- These numbers are flagged in the report as evidence of internal consistency, **not** generalization.

**Paper framing (section — ML Evaluation, honest version)**

> We evaluate the categorizer on a corpus of 7,194 labeled transactions drawn from a consented third-party MTN SMS export (994 rows, PII hashed at import) and a synthetic corpus generated by rule-driven templating (7,600 rows). Stratified 5-fold cross-validation on the full corpus and a held-out slice of real-only SMS both return near-perfect scores for Random Forest and Logistic Regression, and correspondingly elevated scores for Naive Bayes. We report this result as evidence of internal consistency between the rule-derived labels and the feature encoding, rather than as a generalization metric: both labels and features in the present pipeline are deterministic functions of the same raw signals (transaction type, keyword presence in reference and counterparty name fields), so any sufficiently expressive classifier will approximate the rule system with arbitrarily high fidelity. A paper-honest generalization metric requires a hand-labeled ground-truth sample of real SMS and measurement of model–annotator agreement, alongside inter-annotator agreement (κ) to quantify label noise. Both are flagged as outstanding validation items and are the principal entries in our future-work section of the evaluation chapter.

---

## 2026-04-23 — ML evaluation harness (paper-grade, data-ready)

**What changed**
- [scripts/evaluate.py](../scripts/evaluate.py) — new standalone script. Loads the labeled corpus, produces a stratified 80/20 train/test split, runs 5-fold stratified cross-validation, evaluates on a held-out set, and compares the production Random Forest against three baselines (Logistic Regression, Multinomial Naive Bayes, and a majority-class DummyClassifier) on the same splits.
- [docs/ml_evaluation.md](ml_evaluation.md) — machine-generated report with every number the paper's ML Evaluation section needs: dataset summary, per-class frequency table, CV mean ± std across models, held-out classification report (precision/recall/F1 per class), and confusion matrix. Regenerated by running the script with `--write-md`.

**Why it matters**

The categorizer previously had CV inside `categorizer/train.py`, but that file also fits and *overwrites* the production model. That coupling makes it unsafe to run casually ("did the numbers change?" shouldn't risk touching `model.pkl`), and the output is a training log, not a paper artifact. Evaluation and training are different jobs.

More importantly: the corpus is going to grow. Real SMS samples are the next unblock, and when they arrive the question will be "did the model get better?" — a question you can only answer if you have frozen, reproducible numbers to compare against. This harness is that snapshot. The same script, same seed, same splits, run before and after corpus expansion, gives an apples-to-apples delta. Without it, every improvement is anecdotal.

The baseline comparison is the paper's honest contribution. A 0.98 F1 is meaningless without knowing what the trivial baselines score on the same data. Here, the majority-class baseline hits 0.14 weighted F1 and Naive Bayes hits 0.88 — so the production RF's 0.98 is a real lift, not an artifact of an easy problem. That's the figure reviewers will ask for.

**How it works**

The harness is deliberately read-only. It imports `categorizer.features.extract_batch` so the feature vector is identical to production, but it never touches `categorizer/model.py` or `model.pkl`. Four evaluation passes run on the same data:

1. **Dataset summary.** Sample count, class count, per-class frequency table — surfaces class imbalance up front so no one over-interprets a macro average on a skewed corpus.
2. **Cross-validation across four models.** Each model is fit and scored on the same 5 stratified folds. Weighted F1, macro F1, and accuracy are reported with mean ± std. Classes with fewer samples than the fold count are dropped from CV with explicit disclosure — singleton classes break stratified splits and silently filtering them would hide the corpus gap.
3. **Held-out test-set evaluation.** 80/20 stratified split, RF fit on the train portion, full classification report on the held-out 20%. Singleton classes are filtered here too, with the excluded list printed in the report.
4. **Confusion matrix.** Printed as a markdown table; `--confusion-png` optionally saves a matplotlib heatmap.

The entire run is seed-controlled (default 42, override with `--seed N`). Same seed + same corpus → byte-identical numbers.

**How to verify**

```bash
python scripts/evaluate.py                  # print full report
python scripts/evaluate.py --write-md       # also refresh docs/ml_evaluation.md
python scripts/evaluate.py --confusion-png  # add PNG heatmap
python scripts/evaluate.py --seed 7         # different split, sanity-check stability
```

Current snapshot (406 samples, 15 categories, 2 singleton classes excluded):

- RandomForest CV weighted F1: **0.984 ± 0.025**
- LogisticRegression CV weighted F1: **0.987 ± 0.013**
- MultinomialNB CV weighted F1: **0.883 ± 0.017**
- Majority-class CV weighted F1: **0.139 ± 0.001**
- RF held-out: accuracy **0.975**, weighted F1 **0.963**, macro F1 **0.830**

(Macro F1 is dragged down by `supplier_payment` and `transport`, which have 1 test sample each — a corpus-size story, not a model story.)

**Paper framing (section — ML Evaluation)**

> We evaluate the transaction categorizer on the full labeled corpus using stratified 5-fold cross-validation and a held-out 20% test set. The production Random Forest is compared against three baselines — Logistic Regression, Multinomial Naive Bayes, and a majority-class DummyClassifier — trained on identical feature vectors and identical splits. Cross-validation weighted F1 for the Random Forest is 0.984 ± 0.025, versus 0.883 ± 0.017 for Naive Bayes and 0.139 ± 0.001 for the majority-class baseline, confirming that the learned model captures non-trivial signal from the engineered features (amount buckets, one-hot transaction type, keyword indicators, counterparty presence). Logistic Regression matches the Random Forest's weighted F1 within noise, indicating that the feature space is largely linearly separable at the current corpus size — a finding we will revisit as the corpus grows and non-linear interactions become more likely to dominate. All evaluation runs are deterministic under a fixed seed, and the evaluation harness is read-only with respect to the production model artifact, so reported numbers can be regenerated without risking drift in deployed state.

---

## 2026-04-22 — Data minimization audit

**What changed**
- [docs/data_minimization.md](data_minimization.md) — new audit document that traces every pathway raw SMS takes through the system, names every durable storage mechanism, gives a per-pathway verdict on whether raw SMS is retained, and honestly discloses the two categories of derived data that *do* persist.
- No code changes. This entry is a written-down verification of behaviour that was already true in the code; it turns an implicit property into an auditable claim.

**Why it matters**

MomoParse's privacy story sits in the middle of the paper's ethical considerations section and the pitch to any licensed lender or regulator: **raw SMS text is never persisted to durable storage.** Claiming it is cheap; proving it requires walking every entry point and every storage mechanism and writing down what you find. Until this document existed, the claim was believable but not checkable — a reviewer couldn't verify it without re-reading the codebase themselves.

The audit also forces honest disclosure of what *is* retained. Two derivations outlive the request: the global `CounterpartyProfile` histograms (Layer 3 of the categorizer — the "data moat") and the `JobRecord.result` payloads held for async polling. Neither contains raw SMS, but both are identifying and persistent, and neither has a TTL or user-isolation mechanism today. These are real compliance gaps, and writing them down here means they won't quietly disappear into the assumption that "we're fine on privacy."

For the paper, this slots straight into the Ethical Considerations section: minimization is demonstrated rather than asserted, and the known gaps are flagged as future work rather than elided.

**How it works**

The audit walks five categories:

1. **Entry points.** Five public endpoints receive raw SMS via Pydantic request bodies. Each is linked to its handler with file:line anchors.
2. **Per-pathway verdict.** For each pathway — sync parse, async job, webhook delivery, drift telemetry, database schema, access logs — the document states whether raw SMS is retained and cites the specific code location that either does the retention or structurally prevents it.
3. **What *is* retained.** Honest disclosure of the two persisted derivations, with source, schema, rationale, user-isolation status, and retention policy.
4. **Known gaps.** Five concrete gaps are flagged: no TTL on either persisted table, no user isolation on counterparties, dev-only JSON file shouldn't run in prod, no DSR endpoint, exception messages could theoretically leak.
5. **Recommended next engineering changes.** A pytest that pins the invariant in CI, TTL columns, DSR endpoints, and a README privacy link.

The claim is scoped to *durable* storage — Python's GC handles in-memory cleanup once a function frame exits, and transient retention during a single request or async job is explicitly out of scope.

**How to verify**

```bash
# Confirm DB schema has no sms_text columns
python -c "from db.models import JobRecord, CounterpartyProfile; import pprint; pprint.pp([c.name for c in JobRecord.__table__.columns]); pprint.pp([c.name for c in CounterpartyProfile.__table__.columns])"

# Confirm telemetry emits only a hash prefix, not raw SMS
grep -n "sha256\|sms_prefix\|sms_text" parser/telemetry.py
```

The future-work CI test named in the audit — asserting `sms_text` substrings never appear in response JSON, log records, or job result payloads for a representative request through every endpoint — would pin the invariant deterministically.

**Paper framing (Ethical Considerations section)**

> MomoParse does not persist raw SMS text. We audited every entry point (five public endpoints) and every storage mechanism (two database tables, disk files, structured logs, webhook delivery) and confirmed that raw SMS is used transiently during request handling and is discarded once structured fields are extracted. The one trace that leaves the request is a sixteen-character SHA-256 prefix emitted with drift-telemetry events for correlation — insufficient to reconstruct content. This reflects a design choice consistent with Ghana's Data Protection Act 2012 principle of minimization and with the "user-owned" framing: the user's SMS remains on the user's device; MomoParse receives it, extracts structured fields, and forgets the original text. Two derivations of user data do persist beyond request lifetime — a counterparty intelligence store and completed async job results — and are disclosed with their current limitations (no TTL, no user isolation on the counterparty store, no data-subject-rights endpoint) flagged as known gaps rather than elided.

---

## 2026-04-22 — Template Drift Benchmark published as a named artifact

**What changed**
- [docs/drift_benchmark.md](drift_benchmark.md) — full writeup of the existing drift harness as a reusable, publishable benchmark: motivation, mutation catalogue with operational definitions, test protocol, pass criteria, reproducibility, limitations, future work, and paper-ready framing.
- No code changes. The harness itself has lived in [tests/test_drift.py](../tests/test_drift.py) for some time; this entry upgrades it from "internal test file" to "named contribution."

**Why it matters**

Regex-based SMS parsers are the dominant approach for mobile-money intelligence in places like Ghana because they're auditable, cheap, and don't require server-side model deployment. Their single biggest failure mode — format drift — is widely acknowledged in the alt-credit-scoring literature but has never been systematically measured. Papers mention drift as a limitation; no one has published a benchmark for it.

The drift harness you already built *is* that benchmark. It takes 26 amount-bearing templates, subjects each to seven curated mutations (verb swap, currency drift, field reorder, whitespace bloat, truncation, label abbreviation, promo injection), and asserts the parser still recovers the fields the Financial Health Index actually consumes. 209 test cases, fully deterministic, parametrized so new templates and new mutations require no test code changes. This is a real engineering contribution — it just wasn't packaged as one.

The writeup makes it citable. Reviewers and future researchers can now reference "the MomoParse Template Drift Benchmark" as a concrete artifact rather than a hand-wavy claim. For the paper, this slots directly into section 7 (Validation) and strengthens the novelty statement in section 4 (Related Work — no equivalent benchmark exists in the literature).

**How it works**

Two axes of parametrization compose the full test matrix:

- **Template axis:** every `(telco, template)` pair with an `example` SMS and an amount-bearing `tx_type`, loaded from `configs/mtn_templates.json` and `configs/telecel_templates.json`. Currently 26 templates.
- **Mutation axis:** a fixed list of 7 mutation functions. Each takes a clean SMS and returns `(mutated_sms, applied)`. If the mutation's trigger isn't present in this particular SMS (e.g. `verb_swap` on an SMS that has no swappable verb), it returns `applied=False` and the test skips — keeping skipped cases semantically distinct from failures.

For each applicable cell, the clean SMS is parsed to capture ground truth (`amount`, `tx_type`, `balance`), the mutation is applied, the mutated SMS is re-parsed, and five invariants are asserted: telco preservation, no silent drop (`match_mode` ≠ `none`), amount equality, tx_type equality, confidence in (0, 1] and within the fuzzy cap when applicable.

The passing path may be either exact regex match or the fuzzy fallback — the benchmark prescribes *what* must be recovered, not *how*. Fuzzy recoveries are allowed but capped at confidence ≤ 0.6 and emit telemetry, so production drift is both testable in CI and observable in prod.

**How to verify**

```bash
python -m pytest tests/test_drift.py -v                 # run the benchmark
python -m pytest tests/test_drift.py --collect-only -q  # count current cases (209)
```

**Paper framing (section 7 — Validation, and section 4 — Related Work)**

> We introduce a deterministic drift benchmark that subjects every telco-registered template to seven curated mutations modelling observed format-drift patterns. The benchmark asserts that parser output preserves the fields consumed by downstream credit scoring (amount, tx_type, telco, balance) under every applicable mutation. To our knowledge this is the first published drift benchmark specifically targeting regex-based mobile-money SMS parsers — a class of system whose silent-failure mode has been qualitatively acknowledged in the alt-credit-scoring literature but not systematically measured.

---

## 2026-04-22 — Sensitivity analysis on MFH weights

**What changed**
- [scripts/sensitivity_analysis.py](../scripts/sensitivity_analysis.py) — new standalone script. Perturbs each of the five MFH weights by ±0.10, renormalizes the remaining weights to preserve Σw = 1, recomputes the composite over six canonical user profiles, and reports the largest observed swing.
- [docs/sensitivity_analysis.md](sensitivity_analysis.md) — machine-generated results, regenerated by running the script with `--write-md`.

**Why it matters**

The published MFH weights (30/25/20/15/10) are grounded in the finance and econometrics literature, but any fixed weighting invites the question: *what if we chose slightly different numbers?* If a 10-percentage-point shift in any single weight materially changed the score, MFH would be fragile — reviewers (and lenders) could legitimately dismiss the composite as arbitrary.

The analysis answers that directly. Across six profiles spanning the realistic MoMo user space (high saver, negative saver, volatile trader, salaried, micro-merchant, thin file), a ±0.10 shift in any single weight moves the composite by at most **6.3 points out of 100**. This is the robustness claim the paper's Financial Health Index section needs — MFH is a stable target, not a fragile one.

The most sensitive weight is `transaction_velocity` (max 6.3 pp swing on the Volatile Trader profile). Worth flagging because it's also the smallest published weight (0.10), so a ±0.10 perturbation is proportionally the largest — effectively doubling or zeroing the weight. The least sensitive weight is `savings_rate` (max 1.9 pp), which is reassuring because it's also the weight with the strongest literature support.

**How it works**

For each profile, the script:

1. Computes the baseline composite using the published weights.
2. For each of the five weights, produces a perturbed weight set where that weight is shifted by +0.10 (and a second set with −0.10). The remaining four weights are scaled proportionally so the total still sums to 1.0.
3. Recomputes the composite under each perturbation.
4. Records `|composite_perturbed − composite_baseline|` as the swing for that (profile, weight, direction) combination.
5. The headline number is the maximum swing observed across every (profile, weight, direction) triple.

Profiles are synthetic — fixed points in the sub-score space chosen to stress-test the weighting, not sampled from real data. This is intentional: the claim is about the *method* being robust, which doesn't depend on any particular user.

**How to verify**

```bash
python scripts/sensitivity_analysis.py              # prints markdown report
python scripts/sensitivity_analysis.py --write-md   # refreshes docs/sensitivity_analysis.md
```

Current results in [docs/sensitivity_analysis.md](sensitivity_analysis.md). Rerun any time weights change in [enricher/analytics.py](../enricher/analytics.py) `_INDEX_WEIGHTS`.

**Paper framing (section 6 — Financial Health Index)**

> To test robustness of the published weight distribution, we perturb each weight by ±0.10 — redistributing the shift proportionally across the remaining weights so Σw = 1 is preserved — and recompute the composite across six canonical profiles spanning the sub-score space. The maximum observed change is 6.3 points on a 0–100 scale, confirming that MFH is not fragile to moderate disagreements in weight choice. The most sensitive weight is `transaction_velocity` (max ΔH = 6.3), which is expected: at a published weight of 0.10, a ±0.10 perturbation is proportionally the largest of any weight tested.

---

## 2026-04-22 — Score drivers (reason codes MVP) on the Financial Health Score

**What changed**
- [enricher/analytics.py](../enricher/analytics.py) — new `_compute_score_drivers` helper; `compute_financial_indexes` now returns a `score_drivers` list alongside `composite_health_score`.
- [api/models.py](../api/models.py) — new `ScoreDriver` Pydantic model; `FinancialIndexes` gained a `score_drivers: list[ScoreDriver]` field.
- [tests/test_report.py](../tests/test_report.py) — three new tests covering shape, reconciliation, and end-to-end exposure through `/v1/report`.

**Why it matters**

Before this change, every MFH score was a single opaque number between 0 and 100. A lender looking at "68" had no visibility into whether the user scored that way because their savings are strong but their counterparties are concentrated, or because their income is volatile but their expenses are steady. Those are completely different credit stories, and a lender can't build adverse-action logic on top of a bare number.

Score drivers expose the decomposition that was already being computed internally but never surfaced. The same five indexes that get weighted into the composite are now returned per-request with their normalized value and the points each contributed. This turns MFH from "academic index" into "scorecard" — without adding any new math, ML, or data. For the paper, this is the interpretability contribution.

**How it works**

The composite health score is a weighted sum of five normalized sub-scores:

```
H = 100 × (0.30·Ŝ + 0.25·(1−V̂_I) + 0.20·(1−V̂_E) + 0.15·(1−C) + 0.10·T̂)
```

Each term in that sum is an individual driver. For each index, we compute:

- `normalized` — the sub-score after min/max normalization into [0, 1]. Already existed internally; now returned.
- `contribution_pp` — the sub-score's weight × its normalized value × 100, rounded to an integer. This is the points that sub-score contributed to the final 0–100 composite.

Drivers are sorted by `contribution_pp` descending so the strongest signal is first. The sum of `contribution_pp` across all five drivers equals the composite score (±2 for rounding), *when no low-data penalty applies*. When there's only one month of data, the composite gets a separate −10 penalty and a cap at 70 — the driver decomposition still reflects the pre-penalty composition, which is the honest signal.

**How to verify**

```bash
python -m pytest tests/test_report.py::test_compute_financial_indexes_returns_score_drivers -v
python -m pytest tests/test_report.py::test_score_drivers_sum_reconciles_with_composite -v
python -m pytest tests/test_report.py::test_report_includes_score_drivers -v
```

Or hit the API:

```bash
curl -X POST http://localhost:8000/v1/report \
  -H "X-API-Key: sk-sandbox-momoparse" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"sms_text": "..."}]}' | jq '.financial_indexes.score_drivers'
```

**Paper framing (section 6 — Financial Health Index)**

> Every composite MFH value is accompanied by an additive decomposition into its five constituent sub-scores. Because the composite is a weighted linear sum, attribution is exact by construction — the points each index contributes sum to the composite (up to rounding) when no low-data penalty is applied. This yields interpretable, lender-auditable scoring without post-hoc approximations such as SHAP values that would be required for non-linear models.

---

# MomoParse — Build Log

A running, plain-language record of every non-trivial change. Each entry is written so you can re-read it after time away and re-explain what the system does.

Entries are **reverse chronological** (newest first). Each entry follows:

- **What changed** — files + one-line summary
- **Why it matters** — what the change unlocks or hardens
- **How it works** — the mechanism in plain terms
- **How to verify** — the test or command that proves it

Companion docs: [improvements.md](improvements.md), [ml_evaluation.md](ml_evaluation.md).

---

## 2026-05-22 — Strip academic voice across docs, docstrings, and emitted strings

**What changed**
- New [docs/references.md](references.md) — single consolidated References footer holding the five MFH literature citations (Lusardi & Mitchell, Gottschalk & Moffitt, Morduch & Schneider, Hirschman, Björkegren & Grissen). One file, one place, easy to point at.
- [README.md](../README.md) — dropped the `Reference` column from the MFH table and replaced it with a one-line pointer to `docs/references.md`. Added References to the Docs list. Dropped "published" from the sensitivity-analysis bullet.
- [api/routes/demo.py:849](../api/routes/demo.py#L849) — pipeline step 03 description was "grounded in academic literature"; now lists the five sub-indexes by name (savings rate, income stability, expense volatility, counterparty concentration, transaction velocity).
- [api/models.py:231,279](../api/models.py#L231) — `financial_indexes` description on `ProfileResponse` and `ReportResponse` changed from "Formalized financial indexes grounded in established methodology" to "Five formalized financial indexes plus a composite health score." (Visible in Swagger.)
- [enricher/analytics.py](../enricher/analytics.py) — neutralized the module docstring (no inline citations), the `compute_financial_indexes` and `_score_band` and MFH docstrings (dropped "grounded in established literature," "reviewer," "published"), and the five `# Reference: <citation>` inline comments above each sub-index computation.
- [docs/build_log.md](build_log.md) — stripped all eight "**Paper framing (section X)**" blockquote sections. Renamed the 2026-04-23 ML eval entry to "(deterministic, reproducible)" and the 2026-04-22 drift entry to "documented as a named engineering artifact." Rewrote the "Why it matters" paragraphs that referenced "the paper" / "reviewers" / "novelty statement" / "academic index."
- [docs/ml_evaluation.md](ml_evaluation.md) — "paper-honest" → "generalization-honest"; "annotator" → "labeler."
- [docs/hand_labeling_guide.md](hand_labeling_guide.md) — heading renamed to "Honest Categorizer Accuracy"; "annotator 1 / Cohen's κ" recast as "labeler / inter-rater agreement."
- [docs/drift_benchmark.md](drift_benchmark.md) — "Paper-framed intuition" column → "Why this mutation"; "given paper version" → "given commit." (`## Future work` heading kept by request.)
- [docs/data_minimization.md](data_minimization.md), [docs/improvements.md](improvements.md) — minor: "paper's ethics section" → "data-handling section"; dropped "or academic" from the top-5 framing.
- [docs/sensitivity_analysis.md](sensitivity_analysis.md) + [scripts/sensitivity_analysis.py](../scripts/sensitivity_analysis.py) — "Published weights" → "Weights"; column header "Published w" → "w." Generator and generated doc kept in sync.
- [scripts/evaluate.py](../scripts/evaluate.py) — "paper-grade" → "reproducible"; "paper's ML Evaluation section" → `docs/ml_evaluation.md`; "paper-honest" → "generalization-honest" in both the docstring and the emitted markdown.
- [scripts/score_human_labels.py](../scripts/score_human_labels.py) — "paper-grade" → "reproducible per-category"; emitted section heading "## Paper framing" → "## How to cite this number."
- [categorizer/label_corpus.py:77](../categorizer/label_corpus.py#L77) — comment: "for generalization testing" → "for honest accuracy measurement."

**Why it matters**

MomoParse was carrying paper-arc framing across the codebase even after the 2026-05-04 portfolio reframe. The README hero read as infrastructure, but the moment a reader clicked into `docs/build_log.md` they'd hit eight "**Paper framing (section X)**" blockquotes and conclude it was a paper project that shipped an API along the way. With the Ghana AI Innovation Challenge application going out in 6 weeks (deadline 2026-07-01) — and the application leading with deployed engineering, not published research — every "paper-honest," "reviewer," "novelty statement," and inline citation needed to either move out of the way or be reframed as engineering rigor.

The bar I set: a Bank of Ghana FinTech licensing officer reading the repo should think *"this person built infrastructure I could regulate,"* not *"this person is writing a paper."* The previous state failed that test on docs/build_log.md within one click of the README. After this pass, every surface — README, demo page, Swagger descriptions, build log, ML eval, drift benchmark, sensitivity analysis, hand-labeling guide, evaluation scripts — speaks in engineering voice. The rigor that earns the regulator's read (drift methodology, sensitivity perturbation, rule-derived-label honesty, data-minimization audit) stays visible; it just no longer reads as a manuscript-in-progress.

Citations are not dropped — they're consolidated into [docs/references.md](references.md) so anyone tracing the math back to its source has a single place to look.

**How to verify**

```bash
# No "paper framing" / "paper-grade" / "paper-honest" anywhere outside historical 2026-05-04 context
grep -rn "Paper framing\|paper-grade\|paper-honest\|paper-ready" --include="*.md" --include="*.py" . | grep -v .venv

# Citations live only in docs/references.md (Herfindahl-Hirschman as a term is allowed; it's domain vocabulary)
grep -rn "Lusardi\|Gottschalk\|Moffitt\|Morduch\|Björkegren\|Grissen" --include="*.md" --include="*.py" . | grep -v .venv

# Test suite: same counts as pre-change (no regressions)
python -m pytest -q
# Expected: 293 failed (pre-existing corpus-label drift), 6509 passed, 1856 skipped — total 8658

# Live URLs after Railway redeploy on push
curl -s https://momo-parse.up.railway.app/demo | grep "Compute 5 financial indexes"
curl -s https://momo-parse.up.railway.app/openapi.json | python -c "import sys, json; d=json.load(sys.stdin); print(d['components']['schemas']['ProfileResponse']['properties']['financial_indexes']['description'])"
```

---

## 2026-05-04 — Repo reframe for portfolio framing

**What changed**
- **Deleted** `docs/research_paper_structure.md` and `docs/ml_benchmark.md`. The research-paper outline served the paper-completion arc that's no longer the active framing; the ML benchmark doc described a 406-sample corpus state that's been superseded by the 7,194-sample numbers in [ml_evaluation.md](ml_evaluation.md).
- **Added** a one-paragraph "Why RandomForest" preface at the top of [ml_evaluation.md](ml_evaluation.md) so the model-selection rationale is preserved (just not in its own doc).
- **Rewrote** [docs/improvements.md](improvements.md) as a portfolio-shaped roadmap. Dropped the "paper-critical" tags, the section on data ethics / IRB, the section on outstanding paper sections, and the 5-item Top-5 that mixed academic and commercial milestones. New Top-5 is purely portfolio polish: retrain on the expanded corpus, run the hand-labeling workflow, publish v0.2.0 to PyPI, OpenAPI examples, hashed keys + audit log.
- **Trimmed** "Paper framing" sections from [drift_benchmark.md](drift_benchmark.md) and [data_minimization.md](data_minimization.md). The technical content stays; the "section 7 of the paper" framing comes off.
- **Updated** [README.md](../README.md): inlined the 6-of-8 telco-signal mapping table directly under that paragraph (it used to link to the deleted research_paper_structure.md); updated the Docs list to remove the two deleted entries; rewrote one-line descriptions to drop paper framing.
- **Updated** this build log's preamble — removed the "for the paper" line and the dead links to deleted docs.

**Why it matters**

The repo has been carrying three different framings simultaneously: research paper (with citations, novelty statements, IRB), commercial product (with lender pilots, predictive validity, regulatory positioning), and portfolio piece. The docs reflected all three, which made the project look like it didn't know what it was. A reader (recruiter, lecturer, peer reviewer) skimming the docs would see "improvements roadmap items 41–46: Paper sections still to write" right next to "production hardening: API key hashing" and reasonably wonder which arc the project is actually on.

For a portfolio piece, the right framing is: a self-contained engineering artifact that demonstrates judgment and depth — not a project chasing a venue or a customer. Everything that was paper-only (related work, novelty, threats to validity, IRB sequencing, multi-annotator κ) becomes dead weight. Everything that was commercial-only (lender backtests, regulatory positioning beyond the existing data-minimization audit, a pricing model) likewise drops out. What remains is the engineering: parser, drift benchmark, ML evaluation, score formula + sensitivity analysis, deployed API, real-data validation. That's the showcase.

The rewritten improvements.md surfaces the genuinely-portfolio-shaped follow-ups (retrain, OpenAPI examples, PyPI publish, audit log) while leaving the optional new-scope items (Loan Repayment Punctuality, Income Regularity sub-indexes) as available extensions, not commitments.

**How to verify**

```bash
# Deleted files no longer exist
ls docs/research_paper_structure.md docs/ml_benchmark.md 2>&1 | grep -i "no such"

# No remaining links to deleted docs
grep -rn "research_paper_structure\|ml_benchmark" --include="*.md" . | grep -v .venv

# All docs still listed in README exist
for f in build_log drift_benchmark sensitivity_analysis data_minimization ml_evaluation hand_labeling_guide improvements; do
    test -f "docs/$f.md" && echo "ok: docs/$f.md" || echo "MISSING: docs/$f.md"
done
```

---

## 2026-05-01 — Documentation polish pass for external review

**What changed**
- [README.md](../README.md) — corrected the parser/categorizer architecture diagram from "33 regex templates (11 MTN, 22 Telecel)" to **34 (12 MTN, 22 Telecel)** to match `configs/`; corrected the categorizer corpus breakdown from "2,073 real + synthetic" to **994 real + 6,200 synthetic = 7,194** (the actual training corpus); replaced the 9-row truncated tx_type table with the full **16 distinct slugs** and an explicit MTN-vs-Telecel column noting the `cash_out` / `cash_withdrawal` naming asymmetry; bumped test count "6,500+ → 8,600+"; fixed the `parser/configs/` path to `configs/`; added a one-line note that PyPI lags `main` so users wanting the full pipeline use the git path; turned the unsourced "6 of 8 telco signals" claim into a link to the mapping table in `docs/research_paper_structure.md`. Added a one-line note that the real corpus has grown to 2,073 rows and a model retrain is the natural follow-up.
- `docs/research_paper_structure.md` — updated parser layer from "23 regex templates" to "34 (12 MTN, 22 Telecel) covering 16 distinct tx_type slugs"; corrected feature count from "44" to "31" (matches `categorizer.features.FEATURE_NAMES`); updated training-section sample size from "406" to "7,194 labeled (994 real + 6,200 synthetic)"; rewrote the Validation section to reflect actual current state (8,600+ tests, 209-case drift benchmark, sensitivity analysis, real-data pipeline run); rewrote Future Work to drop already-shipped items. *(File deleted in the 2026-05-04 portfolio reframe — see entry above.)*
- `docs/ml_benchmark.md` — added a top-of-file historical-status banner clarifying that the 406-sample numbers reflect the model-selection rationale at an earlier corpus size; renamed "Current Performance" to "Performance at 406-sample corpus state" to reinforce the temporal scope. *(File deleted in the 2026-05-04 portfolio reframe — see entry above.)*
- [docs/improvements.md](improvements.md) — added a **Status** column to tables A and B; marked items #1 (score_drivers), #6 (sensitivity analysis), #9 (score band calibration), #14 (drift benchmark), #38 (data minimization audit) as **Done** with commit / doc references; rewrote the "Top 5 to do next" section: replaced the now-shipped Apr-2026 list with a **Recently shipped** retrospective and a fresh May-2026 top-5 (IRB submission, predictive-validity backtest with a lender, sub-indexes #7 + #8, Related Work writeup, hashed keys + audit log).

**Why it matters**

A senior engineer (HOD of telecom engineering, intended audience for the next walkthrough) reads numbers carefully. Three different template counts (23 / 26 / 33), two corpus totals (406 / 7,194), and a stale 543-test claim across the docs would be a credibility tax to pay before any technical conversation could start. The polish pass closed every cross-document number mismatch I could find on a full sweep. It also reframed two stale documents that were correct in their day but read as confused alongside the current state — `ml_benchmark.md` now reads as "this is *why* RandomForest, captured at 406 samples" and `ml_evaluation.md` reads as "this is *how the current model performs*, captured at 7,194." Each doc has one coherent story instead of fighting the other.

The Top-5 list in `improvements.md` was the most strategically misleading drift: every item on the previous "actionable now" list has shipped, but the doc still presented them as open. A reader scanning the roadmap would have concluded the project was further behind than it is. The new list reflects what's actually next — IRB, lender backtest, two sub-indexes, Related Work, production hardening — which is also a more honest read of the gap between "demonstrable" and "adoptable."

**How to verify**

```bash
# Stale numbers fully purged from .md files (should return no hits)
grep -rn "543 automated\|6,500+ tests\|33 regex\|11 MTN, 22\|9 transaction types\|14 transaction types\|parser/configs/\|2,073 real + synthetic\|131-case" --include="*.md" . | grep -v .venv

# Ground-truth numbers (current state)
python -c "import json; mtn=json.load(open('configs/mtn_templates.json')); tel=json.load(open('configs/telecel_templates.json')); print('Templates:', len(mtn['templates'])+len(tel['templates']), '(', len(mtn['templates']), 'MTN +', len(tel['templates']), 'Telecel)'); print('Distinct tx_types: MTN', len({t['tx_type'] for t in mtn['templates']}), '/ Telecel', len({t['tx_type'] for t in tel['templates']}))"
python -c "from categorizer.features import FEATURE_NAMES; print('Features:', len(FEATURE_NAMES))"
python -m pytest --collect-only -q 2>&1 | tail -1
```

**Note on the 406 reference at line 230 of this build log:** that entry's snapshot reflects the corpus state on the day it was written. Build log entries are append-only by convention — a re-statement at top-of-file is the right way to surface the current-state numbers, not editing the historical record.

---

## 2026-04-24 — Rolling scoring window + calibrated score bands

**What changed**
- [enricher/analytics.py](../enricher/analytics.py) — `compute_financial_indexes` now accepts a `window_months` parameter (default 6, `None` for lifetime) and applies a rolling window to the transactions it scores. Only the MFH score and its sub-indexes are windowed; the surrounding narrative (monthly breakdown, insights, cash flow totals) still reflects all provided data, matching consumer-credit convention where the score reflects recent behavior but the statement shows full history. New `_score_band()` helper maps every composite to one of four calibrated bands (Poor / Fair / Good / Strong) with published thresholds.
- [api/models.py](../api/models.py) — new `window_months` field on `EnrichRequest` (Pydantic-validated to 1–60 or null); new `ScoreBand` and `ScoringWindow` response models exposed on `FinancialIndexes`. Every `/v1/report` and `/v1/profile` response now carries the band label + range + lender-facing description and the actual date range the score reflects.
- [api/routes/report.py](../api/routes/report.py), [api/routes/enrich.py](../api/routes/enrich.py), [enricher/jobs.py](../enricher/jobs.py) — thread `body.window_months` through both sync and async paths.
- [scripts/demo_report.py](../scripts/demo_report.py) — new `--score-window` flag (default 6, pass 0 for lifetime); the printed report surfaces the band label, the band's plain-English description, and the actual date range the score reflects including how many older transactions were excluded.
- [tests/test_report.py](../tests/test_report.py) — four new tests: window defaults to 6 months and excludes older rows, lifetime mode includes everything, every score gets a band in one of the four buckets, and bands tile 0–100 contiguously without gaps or overlaps. API-level test asserts `score_band` and `scoring_window` are on the `/v1/report` response.
- [README.md](../README.md) — documents the default window, the band thresholds, and the override mechanism.

**Why it matters**

Two gaps in the score's defensibility closed:

First, **users providing different amounts of history were being scored on different windows** without anyone noticing. A demo sample with two months produced one score; a real user pasting four months of data produced another; a three-year export produced a third. Even for the same person on the same day, you got different numbers depending on what you fed in. That's not a credit-scoring tool — that's a sensitivity to input length masquerading as a score. Switching to a rolling 6-month default (FICO / M-Shwari / Tala convention) fixes it at the source: scores are now directly comparable across users and across timeframes, and the API response carries the exact window used so a reviewer can verify the claim. Callers wanting a lifetime view pass `window_months=null` explicitly.

Second, **"27/100" is meaningless without a published threshold table.** A lender needs to know whether 27 is "reject" or "small facility with collateral" or "investigate further." Calibrated bands with documented thresholds turn the bare number into an auditable decision-support signal. The bands are symmetric-ish (0–40 Poor / 41–60 Fair / 61–80 Good / 81–100 Strong) so "Fair" captures the broad middle where most first-time users sit, and the extremes are reserved for decisively weak / strong profiles. Thresholds live in one `_SCORE_BANDS` list that both the runtime and the tests read from — band assignment is a pure lookup, no black box.

Concrete impact on the friend's data: the lifetime score (3.5 years) was 27/100 "Poor," dragged down by old volatile patterns; the default 6-month rolling window gives 43/100 "Fair," which is the honest reflection of *current* financial standing. Same data, same formula, different and more truthful answer.

**How it works**

*Rolling window.* `_apply_rolling_window(transactions, window_months)` finds the latest dated transaction, computes `window_start = window_end - 30 × window_months` days, and keeps only transactions whose date is ≥ `window_start` (undated transactions are kept because they can't be windowed — the enricher's existing logic already handles them by smearing uniformly across months). Lifetime mode (`window_months=None`) short-circuits: the full list is returned untouched. The 30-day-per-month approximation is intentional; calendar-exact windowing would add a `dateutil.relativedelta` dependency for a sub-day difference that doesn't change any score.

*Score bands.* `_SCORE_BANDS` is a list of `(low, high, label, description)` tuples covering 0–100 contiguously. `_score_band(score)` does a linear scan to find the containing band. A dedicated test asserts the bands tile the full range without gaps or overlaps, so changing the thresholds is a one-line edit with a test safety net.

*Back-compat for the async path.* `run_enrich_job` accepts `window_months` as an optional kwarg, and only passes it through when the caller supplied one, so any existing caller (internal or external) that doesn't know about the parameter continues to get the default window from `compute_*` rather than failing with a `TypeError`.

**How to verify**

```bash
# Sync path
curl -X POST http://localhost:8000/v1/report \
  -H "X-API-Key: sk-sandbox-momoparse" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"sms_text":"..."}],"window_months":6}' | jq '.financial_indexes.score_band, .financial_indexes.scoring_window'

# End-to-end demo
python scripts/demo_report.py "<xml>"                        # default 6-month rolling
python scripts/demo_report.py "<xml>" --score-window 0       # lifetime
python scripts/demo_report.py "<xml>" --score-window 12      # 12-month rolling

# Tests
python -m pytest tests/test_report.py::test_scoring_window_defaults_to_6_months \
                 tests/test_report.py::test_scoring_window_lifetime_includes_everything \
                 tests/test_report.py::test_score_band_assigned_to_every_score \
                 tests/test_report.py::test_report_exposes_score_band_and_window -v
```

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

First, **real data matters.** A categorizer trained only on synthetic template-generated SMS is easy to dismiss as a toy. Getting 903 real MTN messages — from a different user, across ~2.5 years of activity, covering marketing filtering, template drift in the wild, and the messy reality of MoMo confirmations that come in pairs — is the first time the system has been exposed to data it did not generate itself. That is the material difference between "works on my test fixtures" and "works on a phone that existed before this project did."

Second, **the data-minimization claim is now enforced in code, not just asserted.** The [data minimization audit](data_minimization.md) written yesterday says raw SMS never persists. The importer now enforces the same posture for training data — third-party names and phones are hashed at import time, and existing rows were retroactively updated so the full corpus is consistent. The "user-owned" data claim is now defensible in the training-set context too, not just the runtime context.

Third, **running the new evaluation pipeline surfaced a real methodological issue** and the honest response was to document it. `label_corpus.py::_label()` assigns categories by inspecting `tx_type + keywords on reference/counterparty`; `features.py` one-hot-encodes `tx_type` and flags the same keywords on the same text. Labels and features are therefore near-isomorphic functions of the same raw signals. Any classifier will score near-perfectly — including on a real-only held-out slice — not because it generalizes, but because the task is effectively an identity map between rule-derived labels and rule-derived features. Recognising this in `docs/ml_evaluation.md` and pointing at the existing item #20 in `docs/improvements.md` (human-labeled ground truth + a second labeler) is the generalization-honest next step. It is a known limitation written down, not a claim silently inflated.

**How it works**

*Import path.* Android SMS Backup & Restore exports XML with one `<sms>` element per message (address, body, date, etc.). The importer iterates, filters on a whitelist of MoMo sender IDs (`MobileMoney`, `MTN`, `Telecel`, `VodafoneCash`, `Vodafone`), runs each body through the project's own parser (`parser.parse(body, sender_id=address)`), and discards `match_mode == none` — that dumps marketing and unknown templates. For each parsed transaction it hashes the extracted counterparty name and phone (SHA-256 → first 10 hex chars, prefixed `name_` / `ph_`), replaces those exact strings in the body, sweeps any remaining Ghana-format phone pattern with the same hash scheme, and redacts `(Current|Available|New|Your new) Balance: GHS X,XXX.XX` to `Balance: GHS [redacted]`. Dedup is by transaction ID against the existing corpus. The same hashing applies to the `counterparty_name`, `counterparty_phone`, and `reference` columns so the CSV row and the body stay in agreement.

*Retroactive redaction.* The `redact-existing` subcommand walks the rows already in the corpus, reads each row's (name, phone), and applies the same redaction pipeline. Rows already in hashed form (name starting `name_`, phone starting `ph_`) are skipped so the operation is idempotent.

*Provenance tagging.* `label_corpus.py` now iterates over a list of `(path, source)` pairs instead of bare paths, writing the tag into a new `source` column. `scripts/evaluate.py::_load_labeled()` reads the tag; `_real_only_holdout()` stratifies the real rows 80/20, trains on `synthetic + real_train`, and scores on `real_test`.

*Honest limitation write-up.* The evaluation report now has a "Known evaluation limitation" section stating in plain terms that near-perfect F1 is expected under the current labeling scheme, what a generalization-honest evaluation would require (human-labeled ground truth + a second labeler), and what this evaluation does tell us (internal consistency of the labeling rules, operational floor guarantee, and baseline separation on the original 406-sample set).

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

---

## 2026-04-23 — ML evaluation harness (deterministic, reproducible)

**What changed**
- [scripts/evaluate.py](../scripts/evaluate.py) — new standalone script. Loads the labeled corpus, produces a stratified 80/20 train/test split, runs 5-fold stratified cross-validation, evaluates on a held-out set, and compares the production Random Forest against three baselines (Logistic Regression, Multinomial Naive Bayes, and a majority-class DummyClassifier) on the same splits.
- [docs/ml_evaluation.md](ml_evaluation.md) — machine-generated report with every number needed to evaluate the categorizer: dataset summary, per-class frequency table, CV mean ± std across models, held-out classification report (precision/recall/F1 per class), and confusion matrix. Regenerated by running the script with `--write-md`.

**Why it matters**

The categorizer previously had CV inside `categorizer/train.py`, but that file also fits and *overwrites* the production model. That coupling makes it unsafe to run casually ("did the numbers change?" shouldn't risk touching `model.pkl`), and the output is a training log, not a comparable evaluation snapshot. Evaluation and training are different jobs.

More importantly: the corpus is going to grow. Real SMS samples are the next unblock, and when they arrive the question will be "did the model get better?" — a question you can only answer if you have frozen, reproducible numbers to compare against. This harness is that snapshot. The same script, same seed, same splits, run before and after corpus expansion, gives an apples-to-apples delta. Without it, every improvement is anecdotal.

The baseline comparison is the honest part of the evaluation. A 0.98 F1 is meaningless without knowing what the trivial baselines score on the same data. Here, the majority-class baseline hits 0.14 weighted F1 and Naive Bayes hits 0.88 — so the production RF's 0.98 is a real lift, not an artifact of an easy problem. That's the figure anyone evaluating the model will ask for.

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

---

## 2026-04-22 — Data minimization audit

**What changed**
- [docs/data_minimization.md](data_minimization.md) — new audit document that traces every pathway raw SMS takes through the system, names every durable storage mechanism, gives a per-pathway verdict on whether raw SMS is retained, and honestly discloses the two categories of derived data that *do* persist.
- No code changes. This entry is a written-down verification of behaviour that was already true in the code; it turns an implicit property into an auditable claim.

**Why it matters**

MomoParse's privacy story is the pitch to any licensed lender or regulator: **raw SMS text is never persisted to durable storage.** Claiming it is cheap; proving it requires walking every entry point and every storage mechanism and writing down what you find. Until this document existed, the claim was believable but not checkable — anyone evaluating the codebase couldn't verify it without re-reading the whole thing themselves.

The audit also forces honest disclosure of what *is* retained. Two derivations outlive the request: the global `CounterpartyProfile` histograms (Layer 3 of the categorizer — the "data moat") and the `JobRecord.result` payloads held for async polling. Neither contains raw SMS, but both are identifying and persistent, and neither has a TTL or user-isolation mechanism today. These are real compliance gaps, and writing them down here means they won't quietly disappear into the assumption that "we're fine on privacy."

This audit is the document a BoG licensing officer would ask for: minimization is demonstrated rather than asserted, and the known gaps are flagged as roadmap items rather than elided.

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

---

## 2026-04-22 — Template Drift Benchmark documented as a named engineering artifact

**What changed**
- [docs/drift_benchmark.md](drift_benchmark.md) — full writeup of the existing drift harness as a reusable benchmark: motivation, mutation catalogue with operational definitions, test protocol, pass criteria, reproducibility, limitations, future work.
- No code changes. The harness itself has lived in [tests/test_drift.py](../tests/test_drift.py) for some time; this entry upgrades it from "internal test file" to "named engineering artifact."

**Why it matters**

Format drift is the central failure mode of regex-based MoMo SMS parsers. Templates that covered 100% of a transaction type yesterday can silently drop 30% of it today after a telco-side template revision — a verb swap, a reordered clause, a swapped currency symbol — and the drop doesn't trigger an error, it just corrupts aggregate indexes downstream. This benchmark turns drift into a measurable, CI-runnable invariant.

The drift harness already in the repo *is* that benchmark. It takes 26 amount-bearing templates, subjects each to seven curated mutations (verb swap, currency drift, field reorder, whitespace bloat, truncation, label abbreviation, promo injection), and asserts the parser still recovers the fields the Financial Health Index actually consumes. 209 test cases, fully deterministic, parametrized so new templates and new mutations require no test code changes.

Promoting it to a named, documented artifact makes it referenceable: future maintainers and integrators can point at "the MomoParse Template Drift Benchmark" as a concrete invariant rather than a hand-wavy claim about robustness.

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

---

## 2026-04-22 — Sensitivity analysis on MFH weights

**What changed**
- [scripts/sensitivity_analysis.py](../scripts/sensitivity_analysis.py) — new standalone script. Perturbs each of the five MFH weights by ±0.10, renormalizes the remaining weights to preserve Σw = 1, recomputes the composite over six canonical user profiles, and reports the largest observed swing.
- [docs/sensitivity_analysis.md](sensitivity_analysis.md) — machine-generated results, regenerated by running the script with `--write-md`.

**Why it matters**

The MFH weights (30/25/20/15/10) are chosen with reference to standard personal-finance and labor-econ metrics, but any fixed weighting invites the question: *what if we chose slightly different numbers?* If a 10-percentage-point shift in any single weight materially changed the score, MFH would be fragile — lenders (and anyone reviewing the score for adoption) could legitimately dismiss the composite as arbitrary.

The analysis answers that directly. Across six profiles spanning the realistic MoMo user space (high saver, negative saver, volatile trader, salaried, micro-merchant, thin file), a ±0.10 shift in any single weight moves the composite by at most **6.3 points out of 100**. The index needs to be defensible against "you just made the weights up" — this is the answer.

The most sensitive weight is `transaction_velocity` (max 6.3 pp swing on the Volatile Trader profile). Worth flagging because it's also the smallest weight (0.10), so a ±0.10 perturbation is proportionally the largest — effectively doubling or zeroing the weight. The least sensitive weight is `savings_rate` (max 1.9 pp), which is reassuring because it's also the weight with the strongest backing in the personal-finance literature.

**How it works**

For each profile, the script:

1. Computes the baseline composite using the documented weights.
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

---

## 2026-04-22 — Score drivers (reason codes MVP) on the Financial Health Score

**What changed**
- [enricher/analytics.py](../enricher/analytics.py) — new `_compute_score_drivers` helper; `compute_financial_indexes` now returns a `score_drivers` list alongside `composite_health_score`.
- [api/models.py](../api/models.py) — new `ScoreDriver` Pydantic model; `FinancialIndexes` gained a `score_drivers: list[ScoreDriver]` field.
- [tests/test_report.py](../tests/test_report.py) — three new tests covering shape, reconciliation, and end-to-end exposure through `/v1/report`.

**Why it matters**

Before this change, every MFH score was a single opaque number between 0 and 100. A lender looking at "68" had no visibility into whether the user scored that way because their savings are strong but their counterparties are concentrated, or because their income is volatile but their expenses are steady. Those are completely different credit stories, and a lender can't build adverse-action logic on top of a bare number.

Score drivers expose the decomposition that was already being computed internally but never surfaced. The same five indexes that get weighted into the composite are now returned per-request with their normalized value and the points each contributed. This turns MFH from a bare composite number into a scorecard — without adding any new math, ML, or data. This is the interpretability story for any lender adopting the score.

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

---

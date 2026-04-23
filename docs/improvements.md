# MomoParse — Improvement Roadmap

Full inventory of work to reach (a) a complete lender-facing tool and (b) a publishable research paper. Each item is tagged:

- **Solidify** — label, expose, or harden work that already exists. Lowest risk, highest leverage.
- **Gap** — table-stakes piece that's missing.
- **New scope** — real additional surface area; requires an explicit decision.

Companion docs: [ml_benchmark.md](ml_benchmark.md), [research_paper_structure.md](research_paper_structure.md).

---

## A. Core pipeline — what a lender needs to actually use it

| # | Item | Tag | Location |
|---|---|---|---|
| 1 | Reason codes / `score_drivers` on every score | Solidify | [enricher/analytics.py](../enricher/analytics.py), [api/routes/report.py](../api/routes/report.py) |
| 2 | Fix report vs. profile asymmetry — both should emit `risk_signals` + drivers + structured `data_confidence` | Solidify | [enricher/analytics.py](../enricher/analytics.py) |
| 3 | Make `data_confidence` structured: `{level, reasons[]}` not a bare string | Solidify | [enricher/analytics.py](../enricher/analytics.py) |
| 4 | Unify income/expense classification — single source, not `_INCOME_CATEGORIES` + `_INCOME_TX_TYPES` fallback | Solidify | [enricher/analytics.py:28-65](../enricher/analytics.py#L28-L65) |
| 5 | Telemetry correlation — link `parse.fuzzy_fallback` events to `request_id` | Solidify | [parser/telemetry.py](../parser/telemetry.py), [api/routes/report.py](../api/routes/report.py) |

## B. Financial indexes — the core research artifact

| # | Item | Tag |
|---|---|---|
| 6 | Sensitivity analysis on MFH weights (±0.1 perturbation study) | Solidify (paper-critical) |
| 7 | Loan Repayment Punctuality index (6th sub-score) | New scope |
| 8 | Income Regularity index (salary-pattern detection over months) | New scope |
| 9 | Score band calibration — map 0–100 to labeled bands with documented thresholds | Gap |

## C. Parser — already strong, some loose ends

| # | Item | Tag |
|---|---|---|
| 10 | Template coverage gaps: reversals, bill payment, international remittance | Gap |
| 11 | Sender ID as hard filter when present (currently only a signal) | Solidify |
| 12 | Batch deduplication on SMS hash | Solidify |
| 13 | Currency normalization (GHS / GH¢ / variants in one helper) | Solidify |
| 14 | Publish the 131-case drift harness as a named benchmark | Solidify (paper-critical) |

## D. ML categorizer — mostly captured in [ml_benchmark.md](ml_benchmark.md) roadmap

| # | Item | Tag | Status |
|---|---|---|---|
| 15 | Expand labeled corpus to 1000+, 50+ per category | Gap (paper-critical) | **Blocked** — waiting on real SMS samples |
| 16 | Held-out test set + stratified 5-fold CV | Solidify (paper-critical) | Blocked on #15 |
| 17 | Baseline benchmarks: Logistic Regression, Naive Bayes | Solidify (paper-critical) | Blocked on #15 |
| 18 | Per-category confusion matrix + precision/recall | Solidify (paper-critical) | Blocked on #15 |
| 19 | Confidence calibration (Platt / isotonic) on `predict_proba` | Solidify | Partially blocked on #15 |
| 20 | Inter-annotator agreement (κ) on a labeled subset | Gap (paper-critical) | Blocked on #15 + second annotator |

## E. API surface — lender-facing polish

| # | Item | Tag |
|---|---|---|
| 21 | `/v1/score` lightweight endpoint — composite + drivers only | New scope |
| 22 | Consent receipts — signed JWT per request with `sms_hash + purpose + timestamp` | New scope |
| 23 | Webhook HMAC signing | Gap |
| 24 | Rate-limit headers on every response | Solidify |
| 25 | API versioning statement in docs (what `/v1` guarantees) | Gap |

## F. Production readiness

| # | Item | Tag |
|---|---|---|
| 26 | Structured logs + metrics (parse success rate, fuzzy fallback rate, p50/p95 latency) | Gap |
| 27 | Error tracking (Sentry or equivalent) | Gap |
| 28 | Load test on `/v1/report` | Gap |
| 29 | API keys hashed in DB, not plaintext | Gap |
| 30 | Audit log — request_id, key hash, endpoint, outcome | Gap |
| 31 | sqlite → Postgres migration path | New scope |

## G. Developer experience

| # | Item | Tag |
|---|---|---|
| 32 | OpenAPI examples on every endpoint | Solidify |
| 33 | `CHANGELOG.md` | Gap |
| 34 | SDK docs expansion | Solidify |
| 35 | Postman / Bruno collection | Gap |

## H. Data & ethics (paper-critical)

| # | Item | Tag | Status |
|---|---|---|---|
| 36 | Expand beyond single-corpus bias (5+ real users) | Gap | Blocked on data |
| 37 | IRB / ethics review (KNUST process) | Gap | Needed before real-user data |
| 38 | Data minimization evidence — audit that raw SMS is never persisted | Solidify | Unblocked |
| 39 | Anonymized dataset release under research license | Gap | Partially blocked on #36 |
| 40 | Seeded RNG, pinned deps, Docker image for reproducibility | Solidify | Unblocked |

## I. Paper sections still to write ([research_paper_structure.md](research_paper_structure.md))

| # | Item |
|---|---|
| 41 | Finish Related Work — technical comparison with Pngme, Mono, Okra |
| 42 | Finish Discussion — what MomoParse cannot capture vs. a full CRB |
| 43 | Threats to validity — construct, external, statistical |
| 44 | Ethical considerations — consent, minimization, adverse-action fairness |
| 45 | Novelty statement — one paragraph vs. Björkegren & Grissen (2018) et al. |
| 46 | Appendix with full regex template list |

---

## Top 5 to do next

Picked for maximum combined leverage on both the **complete tool** and **paper-ready** bars. Originally five; the ones depending on an expanded corpus (#15–20, #36) are blocked until more real SMS samples arrive.

**Adjusted top 5 — actionable now:**

1. **#1 `score_drivers` (MVP first)** — expose sub-score decomposition on every MFH score. Unlocks lender conversation, gives the paper an interpretability contribution. Spec in chat history.
2. **#6 Sensitivity analysis on MFH weights** — one script, high paper value. Shows the weighting choice is robust to perturbation.
3. **#14 Publish the drift harness as a named benchmark** — the novel engineering work is already built; only the writeup remains. Creates a concrete paper contribution.
4. **#38 Data minimization audit + evidence** — verify in code that raw SMS never persists; document in README + paper. Unblocks the ethics section.
5. **ML evaluation scaffolding (prep for #16–18)** — build the harness now so the moment corpus lands, `python scripts/evaluate.py` produces stratified split, CV scores, confusion matrix, and baseline comparisons. Not blocked by data; makes the data unblock instant.

When corpus arrives: #15 → run #16–18 via the scaffolding built in step 5 → #20 (find a second annotator).

# MomoParse — Roadmap

Inventory of follow-up work for the build, organized by area. Items are tagged:

- **Solidify** — label, expose, or harden work that already exists. Lowest risk, highest leverage.
- **Gap** — table-stakes piece that's missing.
- **New scope** — additional surface area; requires an explicit decision.

This list reflects the project's current framing as a portfolio artifact. Items chosen for ongoing technical care, not commercial deadlines.

---

## Recently shipped

- **`score_drivers`** — sub-score decomposition on every MFH score (commit `08b268b`)
- **MFH weight sensitivity analysis** — ±0.10 perturbation study, [sensitivity_analysis.md](sensitivity_analysis.md)
- **Calibrated score bands** — Poor / Fair / Good / Strong with published thresholds (commit `5c0fc2e`)
- **Rolling 6-month scoring window** — FICO/M-Shwari convention, comparable across users (commit `5c0fc2e`)
- **Template Drift Benchmark** — 209-case named benchmark, [drift_benchmark.md](drift_benchmark.md)
- **Data minimization audit** — per-pathway verification, [data_minimization.md](data_minimization.md)
- **ML evaluation harness** — `scripts/evaluate.py`, baselines + CV + held-out test, [ml_evaluation.md](ml_evaluation.md)
- **Real-data validation** — pipeline run against a consented 2,724-message export; surfaced four real-data parser bugs that synthetic fixtures missed
- **Hand-labeling workflow** — stratified sampling + scorer + per-class report, [hand_labeling_guide.md](hand_labeling_guide.md)
- **Drift telemetry** — structured `parse.fuzzy_fallback` log events with 16-char SMS hash for correlation

---

## A. Core pipeline

| # | Item | Tag | Location |
|---|---|---|---|
| 1 | Fix report vs. profile asymmetry — both should emit `risk_signals` + drivers + structured `data_confidence` | Solidify | [enricher/analytics.py](../enricher/analytics.py) |
| 2 | Make `data_confidence` structured: `{level, reasons[]}` not a bare string | Solidify | [enricher/analytics.py](../enricher/analytics.py) |
| 3 | Unify income/expense classification — single source, not `_INCOME_CATEGORIES` + `_INCOME_TX_TYPES` fallback | Solidify | [enricher/analytics.py:28-65](../enricher/analytics.py#L28-L65) |
| 4 | Telemetry correlation — link `parse.fuzzy_fallback` events to `request_id` | Solidify | [parser/telemetry.py](../parser/telemetry.py), [api/routes/report.py](../api/routes/report.py) |

## B. Parser

| # | Item | Tag |
|---|---|---|
| 5 | Template coverage gaps: reversals, international remittance | Gap |
| 6 | Sender ID as hard filter when present (currently only a signal) | Solidify |
| 7 | Batch deduplication on SMS hash | Solidify |
| 8 | Currency normalization (GHS / GH¢ / variants in one helper) | Solidify |

## C. ML categorizer

| # | Item | Tag |
|---|---|---|
| 9 | Retrain on the expanded 2,073-row real corpus (model currently trained on 994 real + 6,200 synthetic) | Solidify |
| 10 | Run the hand-labeling workflow on a stratified 150-row sample for an honest accuracy number | Solidify |
| 11 | Confidence calibration (Platt / isotonic) on `predict_proba` | Solidify |
| 12 | Loan Repayment Punctuality sub-index | New scope |
| 13 | Income Regularity sub-index (salary-pattern detection over months) | New scope |

## D. API surface

| # | Item | Tag |
|---|---|---|
| 14 | `/v1/score` lightweight endpoint — composite + drivers only | New scope |
| 15 | Webhook HMAC signing | Gap |
| 16 | Rate-limit headers on every response | Solidify |
| 17 | API versioning statement in docs (what `/v1` guarantees) | Gap |

## E. Production readiness

| # | Item | Tag |
|---|---|---|
| 18 | Structured logs + metrics (parse success rate, fuzzy fallback rate, p50/p95 latency) | Gap |
| 19 | Load test on `/v1/report` | Gap |
| 20 | API keys hashed in DB, not plaintext | Gap |
| 21 | Audit log — request_id, key hash, endpoint, outcome | Gap |
| 22 | Add TTL to `JobRecord.result` and `CounterpartyProfile` (open gaps from [data_minimization.md](data_minimization.md)) | Gap |

## F. Developer experience

| # | Item | Tag |
|---|---|---|
| 23 | OpenAPI examples on every endpoint | Solidify |
| 24 | `CHANGELOG.md` | Gap |
| 25 | Postman / Bruno collection | Gap |
| 26 | Docker image for reproducibility | Solidify |
| 27 | Publish v0.2.0 to PyPI (currently pinned to v0.1.0; `main` runs ahead) | Gap |

---

## Top 5 to do next

Picked for portfolio polish — visible improvements that show ongoing technical care without committing to commercial milestones.

1. **#9 Retrain the categorizer on the 2,073-row corpus.** The model is still on the 994-row state; retraining and republishing the [ml_evaluation.md](ml_evaluation.md) numbers closes the asymmetry between corpus state and model state. Single command (`python -m categorizer.train` then `python scripts/evaluate.py --write-md`).
2. **#10 Run the hand-labeling workflow.** Workflow + scripts are already built; running it on a stratified 150-row sample produces an honest agreement number that breaks the rule-derived-label loop.
3. **#27 Publish v0.2.0 to PyPI.** Closes the README's "PyPI lags `main`" disclaimer. Workflow exists at `.github/workflows/publish.yml` — needs a tagged release.
4. **#23 OpenAPI examples on every endpoint.** Each endpoint should ship a request + response example so the auto-generated `/docs` page reads as polished, not bare. Pure Pydantic config work.
5. **#20 + #21 Hashed API keys + audit log.** Small lift, large credibility — anyone reviewing the repo for production sensibility checks for these two.

Beyond the top-5, items #12 (Loan Repayment Punctuality) and #13 (Income Regularity) are the two largest "new scope" wins — closing them takes MFH from 5 to 7 of the 8 standard alt-credit signals.

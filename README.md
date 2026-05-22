[![CI](https://github.com/theboylexis/momo-parse-api/actions/workflows/ci.yml/badge.svg)](https://github.com/theboylexis/momo-parse-api/actions/workflows/ci.yml)

# MomoParse — User-Owned Financial Intelligence from Mobile Money SMS

Parse raw Mobile Money SMS messages from MTN and Telecel into structured financial data, categorize transactions with ML, and compute financial health indexes — all from user-owned SMS confirmations.

[**Live demo**](https://momo-parse.up.railway.app/demo) — [**API docs**](https://momo-parse.up.railway.app/docs)

### Who this serves

- **Thin-file borrowers** — Ghanaians with no formal bank history but years of MoMo SMS can now demonstrate income stability and repayment capacity to lenders.
- **Licensed credit scoring entities & digital lenders** — programmatic access to standardized, categorized transaction data for risk models, without building parsing infrastructure from scratch.
- **Users themselves** — transparent visibility into the financial profile telcos already compute internally but never share back.

MomoParse is **infrastructure, not a lender.** Credit scoring is a regulated FinTech activity under Bank of Ghana licensing; MomoParse provides the structured data layer that licensed entities build on top of — keeping the user in control of their own SMS data.

```python
import parser as p

result = p.parse("0000015061132227 Confirmed. You have withdrawn GHS299.58 from A11205 - ACCRA TRADERS on 2025-09-10 at 13:51:07. Your Telecel Cash balance is GHS654.03.")

print(result.telco)       # "telecel"
print(result.tx_type)     # "cash_withdrawal"
print(result.amount)      # 299.58
print(result.balance)     # 654.03
print(result.date)        # "2025-09-10"
print(result.confidence)  # 0.9
```

---

## The Problem

In Ghana's mobile money market (74.6M registered wallets, 23.9M active, GHS 1.00T in Q1 2025 alone — up 74% YoY, on track for ~GHS 4T annually), telcos score users with proprietary algorithms the user never sees. Credit scoring is an officially licensed FinTech activity (15% of 59 approved FinTech entities), yet users generate the data — telcos own the intelligence.

MomoParse inverts this: it extracts **6 of the 8 standard alt-credit signals** from user-owned SMS data alone, transparently and through an open API — so licensed lenders can underwrite the unbanked, and users can see what their own data says about them. The two missing signals — handset location and battery/device habits — require invasive OS-level access that user-owned SMS cannot provide.

| Telco signal (internal) | MomoParse equivalent (from SMS) | Status |
|---|---|---|
| Top-up frequency | Income-side transaction frequency | Captured |
| Transaction volume | Total inflows / outflows | Captured |
| Recharge consistency | Spending regularity | Captured |
| CDR contact diversity | Counterparty diversity (HHI) | Captured |
| Loan repayment history | Recurring payment patterns | Captured |
| ARPU | Average transaction size | Captured |
| Location data | _Not available_ | Requires OS-level access |
| Battery / device habits | _Not available_ | Requires OS-level access |

## Architecture

```
Raw SMS
  ↓
Parser ─────────── 34 regex templates (12 MTN, 22 Telecel) + fuzzy fallback
  ↓
ML Categorizer ─── RandomForest, 7,194 labeled samples (994 real + 6,200 synthetic), 15 categories
  ↓
Financial Indexes ─ 5 formalized indexes → Composite Health Score + per-score drivers
  ↓
Structured JSON
```

Real-SMS corpus has since grown to 2,073 rows (956 MTN + 1,117 Telecel) — retraining the model on the expanded corpus is tracked in [docs/improvements.md](docs/improvements.md).

## Financial Health Index (MFH)

A single composite score (0–100) combining five formalized financial indexes:

**H = 100 × Σ wᵢ · x̂ᵢ**

| Index | Formula | Weight |
|-------|---------|--------|
| Savings Rate | (Income − Expenses) / Income | 30% |
| Income Stability | σ(income) / μ(income) | 25% |
| Expense Volatility | σ(expenses) / μ(expenses) | 20% |
| Counterparty Concentration | Σ(shareᵢ²) | 15% |
| Transaction Velocity | transactions / days | 10% |

See [docs/references.md](docs/references.md) for the literature these indexes draw from.

Each sub-score is min-max normalized to [0, 1] with defined bounds. Inverted indexes (where higher = worse) use (1 − x) so higher always means healthier.

**Rolling window (default 6 months).** MFH scores the most recent 6 months of activity relative to the latest dated transaction — consistent with FICO / M-Shwari / Tala convention so scores are comparable across users regardless of how much history they provide. Callers can override via `window_months` (1–60 months) or pass `null` for lifetime scoring.

**Calibrated score bands.** Every composite maps to a four-band lender-facing label with published thresholds:

| Band | Range | Interpretation |
|---|---:|---|
| **Poor** | 0–40 | Transactional signals do not support extending credit without additional context |
| **Fair** | 41–60 | Borderline — some positive signals, volatility or savings gaps warrant a smaller facility |
| **Good** | 61–80 | Solid financial signals across most indexes |
| **Strong** | 81–100 | Consistently high savings, stable income, diversified counterparties |

## Supported Telcos & Transaction Types

| Telco | Templates | Distinct tx_types |
|-------|---:|---:|
| MTN Mobile Money | 12 | 7 |
| Telecel Cash | 22 | 13 |

16 distinct `tx_type` slugs across both telcos. MTN's `cash_out` and Telecel's `cash_withdrawal` describe the same operation under each telco's native naming — both are preserved as emitted by the parser. Full slug list lives in [`configs/`](configs/).

## Validation

- **8,658 tests** passing — synthetic corpus + 2,073-row real corpus (956 MTN, 1,117 Telecel, PII hashed at import) + unit/integration tests
- **[Template Drift Benchmark](docs/drift_benchmark.md)** — 209-case harness applies seven curated telco-drift mutations (verb swap, currency-symbol drift, field reorder, whitespace bloat, truncation, label abbreviation, promo injection) across every registered template and asserts `amount`, `tx_type`, `telco`, and `balance` still recover
- **[Real-data validation](docs/build_log.md)** — pipeline exercised against a consented 2,724-message SMS export; surfaced and fixed four parser-level defects (failed-transaction counting, fuzzy-match hallucination of airtime purchases, duplicate-notification dedup, sender-whitelist gap) that synthetic fixtures did not expose
- **[MFH Weight Sensitivity Analysis](docs/sensitivity_analysis.md)** — ±0.10 perturbation of each sub-index weight (with proportional redistribution so Σw = 1) shifts the composite by at most 6.3 points across six canonical user profiles; the 30/25/20/15/10 weighting is robust to moderate disagreement
- **Parser robustness** — fuzzy fallback (token-overlap path at capped confidence ≤0.6, with product-noun gating to prevent cross-category contamination), failure / duplicate-notification filter (rejects "failed to send," daily-limit, voucher-expired SMS at parser stage), and drift telemetry (structured `parse.fuzzy_fallback` log events with 16-char SHA-256 SMS hash — no raw SMS body)
- **[Data minimization audit](docs/data_minimization.md)** — every pathway raw SMS takes through the system is traced; no durable store retains it. Known gaps (TTL on job results, counterparty-store user isolation, DSR endpoint) flagged rather than elided
- Parser covers **~95% of national MoMo transaction volume** by category (per BoG Q1 2025 report)

*Source: Bank of Ghana, FinTech and Innovation Office. FinTech Sector Report: 2025 Q1.*

## Installation

```bash
pip install momoparse
```

PyPI hosts the parser package; the categorizer, enricher, and FastAPI service track the `main` branch and may run ahead of the latest tagged release. To get the full pipeline (API + categorizer + enricher + recent scoring features), clone and run locally:

```bash
git clone https://github.com/theboylexis/momo-parse-api
cd momo-parse-api
pip install poetry && poetry install
python examples/basic_parse.py
```

## Quick Start

```python
import parser as p

result = p.parse(sms_text)                            # auto-detect telco
result = p.parse(sms_text, sender_id="MobileMoney")   # sender ID improves detection
result.to_dict()                                      # full field dict
```

Fields on `ParseResult`: `telco`, `tx_type`, `amount`, `balance`, `fee`, `counterparty_name`, `counterparty_phone`, `tx_id`, `reference`, `date`, `time`, `confidence`, `match_mode`. Schema with types and examples at [/docs](https://momo-parse.up.railway.app/docs).

## API

The [MomoParse API](https://momo-parse.up.railway.app/docs) adds:

- **Categorization** — auto-assigns financial categories (rent, salary, merchant payment, etc.)
- **Enrichment** — aggregate analytics from 1,000+ SMS in one call
- **Financial profiles** — indexes, health score, risk signals

**Free sandbox key:** `sk-sandbox-momoparse` — 100 calls/day, no sign-up.

```bash
curl -X POST https://momo-parse.up.railway.app/v1/parse \
  -H "X-API-Key: sk-sandbox-momoparse" \
  -H "Content-Type: application/json" \
  -d '{"sms_text": "YOUR_SMS_HERE"}'
```

## Docs

- [Build Log](docs/build_log.md) — running plain-language record of every non-trivial change
- [Template Drift Benchmark](docs/drift_benchmark.md) — the 209-case reproducible benchmark for regex-based MoMo SMS parsers
- [MFH Weight Sensitivity Analysis](docs/sensitivity_analysis.md) — robustness of the 30/25/20/15/10 weighting under ±0.10 perturbation
- [Data Minimization Audit](docs/data_minimization.md) — per-pathway verification that raw SMS never persists; honest disclosure of what derived data does
- [ML Evaluation](docs/ml_evaluation.md) — categorizer state: 7,194-sample dataset, stratified 5-fold CV, baselines, held-out test, confusion matrix; honest section on rule-derived labels
- [Hand-Labeling Guide](docs/hand_labeling_guide.md) — workflow for human-labeled evaluation that breaks the rule-derived-label loop
- [Roadmap](docs/improvements.md) — tagged inventory of solidify/gap/new-scope items, with current Top-5 next steps
- [References](docs/references.md) — the literature the five MFH sub-indexes draw from
- [Project Board](https://github.com/users/theboylexis/projects/1) — task tracking

## Contributing

Issues and PRs welcome. Parser templates live in [`configs/`](configs/) — adding a new template is a single JSON object.

## License

MIT — Copyright © 2025–2026 Alex Marfo. See [LICENSE](LICENSE).

---

Built by Alex Marfo ([@theboylexis](https://github.com/theboylexis)) — sole creator and maintainer. [Portfolio](https://alexmarfo.vercel.app) · [Build notes](https://alexmarfo.vercel.app/blog/building-momo-parse-api).

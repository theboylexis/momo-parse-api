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

MomoParse inverts this: it extracts **6 of 8 telco credit scoring signals** from user-owned SMS data alone, transparently and through an open API — so licensed lenders can underwrite the unbanked, and users can see what their own data says about them.

## Architecture

```
Raw SMS
  ↓
Parser ─────────── 33 regex templates (11 MTN, 22 Telecel) + fuzzy fallback
  ↓
ML Categorizer ─── RandomForest, 7,194 labeled samples (2,073 real + synthetic), 15 categories
  ↓
Financial Indexes ─ 5 formalized indexes → Composite Health Score + per-score drivers
  ↓
Structured JSON
```

**Pipeline layers:**

| Layer | Method | Purpose |
|-------|--------|---------|
| Parser | Rule-based (regex templates) | Extract fields: amount, balance, fee, counterparty, date, tx_id |
| Categorizer | 3-layer (rules → ML → counterparty learning) | Classify into financial categories |
| Enricher | Statistical analysis | Compute financial indexes and health score |

## Financial Health Index (MFH)

A single composite score (0–100) combining five formalized financial indexes:

**H = 100 × Σ wᵢ · x̂ᵢ**

| Index | Formula | Weight | Reference |
|-------|---------|--------|-----------|
| Savings Rate | (Income − Expenses) / Income | 30% | Lusardi & Mitchell (2014) |
| Income Stability | σ(income) / μ(income) | 25% | Gottschalk & Moffitt (1994) |
| Expense Volatility | σ(expenses) / μ(expenses) | 20% | Morduch & Schneider (2017) |
| Counterparty Concentration | Σ(shareᵢ²) | 15% | Hirschman (1964) |
| Transaction Velocity | transactions / days | 10% | Björkegren & Grissen (2018) |

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

| Telco | Templates |
|-------|-----------|
| MTN Mobile Money | 9 transaction types |
| Telecel Cash | 14 transaction types |

| Transaction Type | Slug |
|---|---|
| Transfer sent | `transfer_sent` |
| Transfer received | `transfer_received` |
| Cash withdrawal (agent) | `cash_withdrawal` |
| Cash deposit (agent) | `cash_in` |
| Airtime purchase | `airtime_purchase` |
| Merchant payment | `merchant_payment` |
| Loan repayment | `loan_repayment` |
| Bank transfer | `bank_transfer` |
| Wallet balance | `wallet_balance` |

## Validation

- **6,500+ tests** passing — synthetic corpus + 2,073-row real corpus (956 MTN, 1,117 Telecel, PII hashed at import) + unit/integration tests
- **[Template Drift Benchmark](docs/drift_benchmark.md)** — 209-case harness applies seven curated telco-drift mutations (verb swap, currency-symbol drift, field reorder, whitespace bloat, SMS truncation, label abbreviation, promo injection) across every registered template and asserts `amount`, `tx_type`, `telco`, and `balance` still recover
- **[Real-data end-to-end validation](docs/build_log.md)** — pipeline exercised against a consented 2,724-message SMS export; surfaced and fixed four parser-level defects (failed-transaction counting, fuzzy-match hallucination of airtime purchases, duplicate-notification dedup bug, sender whitelist gap) that synthetic fixtures did not expose
- **[MFH Weight Sensitivity Analysis](docs/sensitivity_analysis.md)** — ±0.10 perturbation of each sub-index weight, with proportional redistribution so Σw = 1 is preserved, shifts the composite score by at most 6.3 points across six canonical user profiles — the published 30/25/20/15/10 weighting is robust to moderate disagreement
- **Fuzzy fallback with product-noun gating** — when no regex matches exactly, a token-overlap + generic field regex path recovers partial data at capped confidence (≤0.6). Fuzzy candidates for product-bearing tx_types (airtime, bundle, loan, interest) are rejected unless the SMS contains the product noun, preventing cross-category contamination
- **Failed / duplicate-notification filter** — SMS describing failures ("failed to send", "exceeded your daily transaction limit", "has failed at", "expired and has been returned") and low-info duplicate notifications are rejected at the parser stage with `match_mode=none`, preventing phantom transactions from inflating category totals
- **Drift telemetry** — every fuzzy fallback emits a structured `parse.fuzzy_fallback` JSON log line (`template_id`, `missing_critical_fields`, SHA-256 SMS hash — no raw SMS body) so aggregating a week of production logs surfaces exactly which templates need a revision
- **[Data minimization audit](docs/data_minimization.md)** — every pathway raw SMS takes through the system is traced; no durable store retains it. Known gaps (TTL on job results, counterparty-store user isolation, DSR endpoint) flagged rather than elided
- Parser covers **~95% of national MoMo transaction volume** by category (per BoG Q1 2025 report)

*Source: Bank of Ghana, FinTech and Innovation Office. FinTech Sector Report: 2025 Q1.*

## Installation

```bash
pip install momoparse
```

Or clone and run locally:

```bash
git clone https://github.com/theboylexis/momo-parse-api
cd momo-parse-api
pip install poetry && poetry install
python examples/basic_parse.py
```

## Quick Start

```python
import parser as p

# Basic parse
result = p.parse(sms_text)

# With sender ID (improves telco detection)
result = p.parse(sms_text, sender_id="MobileMoney")

# Access fields
result.telco          # "mtn" | "telecel" | "unknown"
result.tx_type        # "transfer_sent" | "cash_withdrawal" | ...
result.amount         # float or None
result.balance        # float or None
result.fee            # float (0.0 if no fee)
result.counterparty_name   # str or None
result.counterparty_phone  # str or None
result.tx_id          # str or None
result.reference      # str or None
result.date           # "YYYY-MM-DD" or None
result.time           # "HH:MM:SS" or None
result.confidence     # float in [0, 1] — continuous weighted-field score
result.match_mode     # "exact" | "fuzzy" | "none" — which path produced the result

# Dict output
result.to_dict()
```

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

- [Build Log](docs/build_log.md) — running plain-language record of every non-trivial change, with paper-section framing
- [Template Drift Benchmark](docs/drift_benchmark.md) — the 209-case reproducible benchmark for regex-based MoMo SMS parsers
- [MFH Weight Sensitivity Analysis](docs/sensitivity_analysis.md) — robustness of the 30/25/20/15/10 weighting under ±0.10 perturbation
- [Data Minimization Audit](docs/data_minimization.md) — per-pathway verification that raw SMS never persists; honest disclosure of what derived data does
- [ML Evaluation](docs/ml_evaluation.md) — machine-generated CV scores, baselines, confusion matrix, with a known-limitations section on rule-derived labels
- [Improvements Roadmap](docs/improvements.md) — tagged inventory of solidify/gap/new-scope items
- [ML Benchmark](docs/ml_benchmark.md) — model performance, feature importances, honest limitations
- [Project Board](https://github.com/users/theboylexis/projects/1) — roadmap and task tracking

## Contributing

Issues and PRs welcome. Parser templates live in `parser/configs/` — adding a new template is a single JSON object.

## License

MIT — Copyright © 2025–2026 Alex Marfo. See [LICENSE](LICENSE).

---

Built by Alex Marfo ([@theboylexis](https://github.com/theboylexis)) — sole creator and maintainer. [Portfolio](https://alexmarfo.vercel.app) · [Build notes](https://alexmarfo.vercel.app/blog/building-momo-parse-api).

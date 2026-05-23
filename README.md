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
Financial Indexes ─ 5 sub-scores → Composite Health Score + per-sub-score drivers
  ↓
Structured JSON
```

Real-SMS corpus has since grown to 2,073 rows (956 MTN + 1,117 Telecel) — retraining the model on the expanded corpus is tracked in [docs/improvements.md](docs/improvements.md).

## Financial Health Index (MFH)

A single composite score (0–100) combining five sub-scores:

| Index | Formula | Weight |
|-------|---------|--------|
| Savings Rate | (Income − Expenses) / Income | 30% |
| Income Stability | σ(income) / μ(income) | 25% |
| Expense Volatility | σ(expenses) / μ(expenses) | 20% |
| Counterparty Concentration | Σ(shareᵢ²) | 15% |
| Transaction Velocity | transactions / days | 10% |

Each sub-score is normalized to [0, 1] and combined as a weighted sum × 100. The composite is returned alongside per-sub-score contributions (additive, exact by construction — no SHAP needed) so a lender can see *why* a score landed where it did.

**Rolling window (default 6 months).** MFH scores the most recent 6 months of activity relative to the latest dated transaction — same convention as FICO / M-Shwari / Tala, so scores are comparable across users regardless of how much history they provide. Override via `window_months` (1–60) or pass `null` for lifetime scoring.

**Score bands.** Every composite maps to a four-band lender-facing label:

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
- **[Template Drift Benchmark](docs/drift_benchmark.md)** — 209-case harness runs in CI; for every template, applies seven realistic telco wording changes (verb swap, currency-symbol drift, field reorder, whitespace bloat, truncation, label abbreviation, promo injection) and asserts the parser still recovers `amount`, `tx_type`, `telco`, `balance`. Turns silent format drift into a loud test failure.
- **Real-data validation** — pipeline exercised against a consented 2,724-message SMS export; surfaced and fixed four parser-level defects (failed-transaction counting, fuzzy-match misclassification of airtime, duplicate-notification dedup, sender-whitelist gap) that synthetic fixtures did not expose. Details in [build log](docs/build_log.md).
- **Parser robustness** — three defenses against real-world telco SMS messiness: (1) a fuzzy fallback for SMS that don't match any template exactly, with a guard that prevents misclassifying a generic merchant payment as airtime; (2) a filter that rejects "Failed to send," daily-limit, and voucher-expired SMS so they don't inflate transaction totals; (3) drift telemetry that logs which templates needed fuzzy matching, using a hash of the SMS for correlation — never the SMS text itself.
- **Privacy posture** — raw SMS is never persisted; each message is processed in-request and the original text discarded. Auth + per-key rate limits on every endpoint. Per-pathway audit and known TODOs in [docs/data_minimization.md](docs/data_minimization.md).
- Parser covers **~95% of national MoMo transaction volume** by category (Bank of Ghana FinTech Sector Report, Q1 2025).

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

- [Build Log](docs/build_log.md) — running record of every non-trivial change, plain language
- [Template Drift Benchmark](docs/drift_benchmark.md) — what the 209-case CI invariant guarantees
- [Data Minimization](docs/data_minimization.md) — per-pathway verification that raw SMS never persists, plus known TODOs
- [ML Evaluation](docs/ml_evaluation.md) — categorizer metrics on the 7,194-sample corpus; how to re-run them
- [Hand-Labeling Guide](docs/hand_labeling_guide.md) — workflow for producing an honest, human-labeled accuracy number
- [Roadmap](docs/improvements.md) — current Top-5 next steps + tagged backlog
- [Project Board](https://github.com/users/theboylexis/projects/1) — task tracking

## Contributing

Issues and PRs welcome. Parser templates live in [`configs/`](configs/) — adding a new template is a single JSON object.

## License

MIT — Copyright © 2025–2026 Alex Marfo. See [LICENSE](LICENSE).

---

Built by Alex Marfo ([@theboylexis](https://github.com/theboylexis)) — sole creator and maintainer. [Portfolio](https://alexmarfo.vercel.app) · [Build notes](https://alexmarfo.vercel.app/blog/building-momo-parse-api).

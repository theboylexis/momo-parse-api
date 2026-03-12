# MomoParse

**Transaction Intelligence API for Mobile Money SMS**

MomoParse transforms raw MoMo SMS messages into structured, categorized financial data. It is the "Plaid Enrich" for mobile money markets — an infrastructure layer that fintechs, banks, and developers plug into to understand a user's MoMo financial life.

**Launch market:** Ghana → West Africa → Pan-African
**Status:** Phase 1 — Parser Engine (Weeks 1–4)

---

## What It Does

**Input:** Raw MoMo SMS text from any Ghanaian telco (MTN MoMo, Telecel Cash)

**Output:** Structured JSON

```json
POST /v1/parse
{
  "sms_text": "Payment made for GHS 150.00 to KWAME ASANTE. Current Balance: GHS 1,230.50. Reference: rent. Transaction ID: 76664093335. Fee charged: GHS 1.12 TAX charged: GHS 0.00.",
  "sender_id": "MobileMoney"
}
```

```json
{
  "telco": "mtn",
  "tx_type": "transfer_sent",
  "template_id": "mtn_transfer_sent_v2",
  "confidence": 1.0,
  "amount": 150.00,
  "currency": "GHS",
  "balance": 1230.50,
  "fee": 1.12,
  "counterparty": {
    "name": "KWAME ASANTE",
    "phone": null
  },
  "tx_id": "76664093335",
  "reference": "rent",
  "date": null,
  "time": null
}
```

---

## Architecture

The parser runs as a **3-stage pipeline**:

```
Raw SMS
   │
   ▼
┌─────────────────────┐
│  Stage 1            │  TelcoDetector
│  Telco Detection    │  sender_id → content patterns
│                     │  confidence: 1.0 (sender) / 0.9 (content)
└────────┬────────────┘
         │ telco name
         ▼
┌─────────────────────┐
│  Stage 2            │  TemplateMatcher
│  Template Matching  │  loads configs/{telco}_templates.json
│                     │  scores each regex template → best match
└────────┬────────────┘
         │ template + match object
         ▼
┌─────────────────────┐
│  Stage 3            │  FieldExtractor
│  Field Extraction   │  applies field rules from template
│                     │  normalizes amounts, phones, names
└────────┬────────────┘
         │
         ▼
     ParseResult
```

**Adding a new telco = add one JSON file to `configs/`. No code changes.**

---

## Project Structure

```
momoparse/
├── parser/               # Core parsing engine (Phase 1)
│   ├── pipeline.py       # MoMoParser — orchestrates all 3 stages
│   ├── detector.py       # Stage 1: telco detection
│   ├── matcher.py        # Stage 2: template matching + confidence scoring
│   ├── extractor.py      # Stage 3: field extraction + normalization
│   ├── models.py         # ParseResult dataclass
│   ├── config_loader.py  # JSON template loader with caching
│   └── normalizers.py    # Amount / phone / name normalization
│
├── api/                  # FastAPI server (Phase 1, Week 3)
│
├── configs/              # Telco template registries (pluggable)
│   ├── mtn_templates.json
│   └── telecel_templates.json
│
├── corpus/               # SMS dataset
│   ├── real_sms_corpus.csv     # Ground truth (76 real annotated SMS)
│   └── synthetic_sms_corpus.csv
│
├── tests/                # Test suite (Week 2)
│
├── docs/                 # API documentation (Week 3)
│
└── pyproject.toml        # Poetry dependency management
```

---

## Supported Transaction Types

| Type | MTN | Telecel |
|------|-----|---------|
| Transfer sent | ✅ (v1 + v2 + with_phone) | ✅ |
| Transfer received | ✅ | ✅ |
| Cash out / withdrawal | ✅ | ✅ |
| Airtime purchase | ✅ | ✅ |
| Airtime received | — | ✅ |
| Merchant payment | ✅ | ✅ |
| Bill / service payment | ✅ | — |
| Bank transfer | — | ✅ |
| Deposit received | — | ✅ |
| Loan repayment | — | ✅ |
| Interest received | — | ✅ |
| Wallet balance | — | ✅ |

---

## Quick Start

```bash
# Install dependencies
poetry install

# Run the parser directly
python -c "
import parser as p
result = p.parse('Payment made for GHS 50.00 to KOFI MENSAH. Current Balance: GHS 200.00. Reference: food. Transaction ID: 76289975115. Fee charged: GHS 0.00 TAX charged: GHS 0.00.', 'MobileMoney')
print(result.to_dict())
"
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| API Framework | FastAPI + Pydantic |
| Database | PostgreSQL 16 |
| Cache / Rate limiting | Redis |
| Testing | pytest + hypothesis |
| Docs | Mintlify |
| Hosting | Railway / Fly.io |
| CI/CD | GitHub Actions |

---

## Roadmap

- **Phase 1 (Weeks 1–4):** Parser engine + FastAPI server + Python SDK
- **Phase 2 (Weeks 5–8):** ML categorization + enrichment + first customers
- **Phase 3 (Weeks 9–12):** Scale, multi-country, enterprise features

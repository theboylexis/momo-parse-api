# momo-parser — Open-Source MoMo SMS Parser for Ghana

Parse raw Mobile Money SMS messages from MTN, Telecel, and AirtelTigo into structured JSON in one line of Python.

```python
import parser as p

result = p.parse("0000015061132227 Confirmed. You have withdrawn GHS299.58 from A11205 - ACCRA TRADERS on 2025-09-10 at 13:51:07. Your Telecel Cash balance is GHS654.03.")

print(result.telco)       # "telecel"
print(result.tx_type)     # "cash_withdrawal"
print(result.amount)      # 299.58
print(result.balance)     # 654.03
print(result.date)        # "2025-09-10"
print(result.confidence)  # 0.97
```

---

## What it does

MoMo SMS messages are unstructured text. Every telco writes them differently. Every transaction type has a different format. This parser handles all of it.

**Input:** Raw SMS string (optionally + sender ID for better telco detection)
**Output:** Structured `ParseResult` with all financial fields extracted

```json
{
  "telco": "telecel",
  "tx_type": "cash_withdrawal",
  "amount": 299.58,
  "currency": "GHS",
  "balance": 654.03,
  "fee": 0.0,
  "counterparty": {
    "name": "ACCRA TRADERS",
    "phone": "A11205"
  },
  "tx_id": "0000015061132227",
  "date": "2025-09-10",
  "time": "13:51:07",
  "confidence": 0.97
}
```

## Supported telcos & transaction types

| Telco | Supported |
|---|---|
| MTN Mobile Money | Yes |
| Telecel Cash | Yes |
| AirtelTigo Money | Yes |

| Transaction type | Slug |
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

## How it works

The parser runs a 3-stage pipeline:

```
Raw SMS
  │
  ▼
Stage 1: Telco Detection
  Keyword + sender-ID signals identify the telco.
  │
  ▼
Stage 2: Template Matching
  Regex templates for each (telco, tx_type) pair.
  Best-scoring template wins.
  │
  ▼
Stage 3: Field Extraction
  Named capture groups extract amount, balance, fee,
  counterparty, date, time, tx_id, reference.
  │
  ▼
ParseResult (structured dict + confidence score)
```

Confidence score: `1.0` = perfect match, `0.8` = partial match, `0.0` = unrecognized.

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

## Quick start

```python
import parser as p

# Basic parse
result = p.parse(sms_text)

# With sender ID (improves telco detection)
result = p.parse(sms_text, sender_id="MobileMoney")

# Access fields
result.telco          # "mtn" | "telecel" | "airteigo" | "unknown"
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
result.confidence     # float in [0, 1]

# Dict output
result.to_dict()
```

## Want more?

The open-source parser handles extraction. The [MomoParse API](https://web-production-5aa38.up.railway.app/docs) adds:

- **Categorization** — auto-assigns a financial category (rent, salary, merchant payment, etc.)
- **Enrichment** — aggregate analytics from 1,000+ SMS in one call
- **Financial profiles** — monthly income, expense ratio, business activity score, risk signals

Perfect for fintech apps, lending platforms, and MFIs that need structured financial data from MoMo users.

**Free sandbox key:** `sk-sandbox-momoparse` — 100 calls/day, no sign-up.

```bash
curl -X POST https://web-production-5aa38.up.railway.app/v1/parse \
  -H "X-API-Key: sk-sandbox-momoparse" \
  -H "Content-Type: application/json" \
  -d '{"sms_text": "YOUR_SMS_HERE"}'
```

## Contributing

Issues and PRs welcome. The parser templates live in `parser/configs/` — adding a new template is a single JSON object.

## License

MIT — use freely. The categorization model and enrichment layer are proprietary.

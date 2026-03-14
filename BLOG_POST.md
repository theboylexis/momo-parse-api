# How I parse 15+ MoMo SMS formats with 95% accuracy

Mobile Money is how West Africa moves money. In Ghana alone, MTN MoMo, Telecel Cash, and AirtelTigo Money process millions of transactions daily — all confirmed via SMS. If you want to build financial tools for these users, that SMS inbox is your data source.

The problem: those messages are unstructured text. Every telco writes them differently. Every transaction type has its own format. There's no API. You get a string and you're on your own.

This is how I built a parser that handles 15+ distinct SMS formats reliably.

---

## The problem, concretely

Here are three real SMS messages from three different telcos, all representing the same transaction type (money sent):

**MTN:**
```
Payment made for GHS 50.00 to DAVID BOATENG. Current Balance: GHS 450.00. Reference: school fees. Transaction ID: 76712833868. Fee charged: GHS 0.50
```

**Telecel:**
```
0000015061132227 Confirmed. You have sent GHS50.00 to 0241234567 - JOHN MENSAH on 2025-09-10 at 13:51:07. Your Telecel Cash balance is GHS654.03.
```

**AirtelTigo:**
```
TXN 987654321. GHS 30.00 sent to KWAME ASANTE (0271234567). Balance: GHS 120.50. Thank you for using AirtelTigo Money.
```

Same event. Completely different structure. Different field names, different ordering, different date formats, different ways of expressing the counterparty.

A naive approach — split on spaces, look for "GHS" — fails immediately on edge cases like fee extraction, missing fields, or transaction IDs that look like phone numbers.

---

## The architecture: 3-stage pipeline

I settled on a regex template system with three stages.

### Stage 1: Telco detection

Before matching templates, I need to know which telco sent the message. I use a combination of:

- **Keyword signals** — "Telecel Cash", "MobileMoney", "AirtelTigo Money" appear in most messages
- **Sender ID** — if the app passes the sender ID (e.g. "MobileMoney", "TelecelCash"), that's a strong signal
- **Structural patterns** — MTN always starts with "Payment made for" or "Payment received for"; Telecel messages start with a 16-digit transaction ID

Telco detection returns a confidence score. If confidence is below threshold, I fall back to trying all templates and taking the highest-scoring match.

### Stage 2: Template matching

Each (telco, transaction_type) pair has one or more regex templates. For example, `(mtn, transfer_sent)` has this template:

```python
r"Payment made for GHS (?P<amount>[\d,]+\.?\d*) to (?P<counterparty_name>[A-Z ]+)\."
r".*Current Balance: GHS (?P<balance>[\d,]+\.?\d*)\."
r".*Reference: (?P<reference>[^.]+)\."
r".*Transaction ID: (?P<tx_id>\d+)\."
r".*Fee charged: GHS (?P<fee>[\d,]+\.?\d*)"
```

Named capture groups do the field extraction. Every significant field — amount, balance, fee, counterparty name, counterparty phone, date, time, transaction ID, reference — gets its own named group.

I score each template by the number of named groups that matched. A template that captures 8/9 fields scores higher than one that captures 5/9. The best-scoring template wins.

### Stage 3: Field normalization

Raw captures need cleaning:

- **Amounts**: strip commas, cast to float (`"1,299.50"` → `1299.50`)
- **Dates**: normalize to ISO 8601 — Telecel uses `YYYY-MM-DD`, some AirtelTigo messages use `DD/MM/YYYY`
- **Phone numbers**: strip leading zeros, country code variations
- **Names**: strip trailing punctuation left by greedy matches

The result is a `ParseResult` object with typed fields and a confidence score between 0 and 1.

---

## Where it gets hard: the edge cases

### Overlapping patterns

A 16-digit number at the start of a Telecel message is a transaction ID. An 11-digit number mid-message is probably a phone number. A 10-digit number could be either. I use positional context in the regex — anchors and lookaheads — to disambiguate.

### Greedy counterparty names

Names like "ACCRA TRADERS" or "JOHN MENSAH BOATENG" are tricky because they can vary in word count. I use `[A-Z][A-Z ]+` with a lookahead for the next known delimiter (usually " on ", " - ", or a period). Occasionally a name contains a hyphen (`KWAME ASANTE-MENSAH`) which breaks naive `[A-Z ]+` patterns. I handle this with a secondary pattern that allows hyphens after at least two words.

### Missing fields

Wallet-to-wallet transfers often don't include a fee. Balance queries don't have a counterparty. Airtime purchases never have a reference. Templates must be tolerant of missing fields — making groups optional with `?` where appropriate, but still assigning a penalty to templates that match fewer groups.

### Multi-line messages

Some SMS arrive as multi-line strings (when the OS splits long messages). I strip newlines and normalize whitespace before matching.

---

## The confidence score

Every `ParseResult` has a `confidence` field between 0 and 1:

- `1.0` — template matched all expected groups; telco detected with high certainty
- `0.8-0.99` — partial match (some optional fields missing) or telco detected via keywords rather than sender ID
- `0.5-0.79` — fell back to generic template; fields extracted but telco uncertain
- `0.0` — no template matched; message is unrecognized

In production, I filter out results below `0.6` confidence before passing to downstream enrichment. Unrecognized messages are logged for template improvement.

---

## What I learned

**1. Regex is the right tool here.** I tried training a sequence model (token classification with a small BERT variant) to extract amounts and names. It was slower, harder to debug, and performed worse on rare transaction types with fewer training examples. Regex templates are fast, interpretable, and easy to extend.

**2. Named groups beat positional groups.** `(?P<amount>...)` instead of `(...)` makes the extraction code clean and the templates self-documenting.

**3. Confidence scoring pays off.** Being explicit about uncertainty lets downstream systems make better decisions — a lending platform can request manual review for low-confidence parses rather than silently ingesting wrong amounts.

**4. Template coverage is the real work.** The parser architecture took two days to build. Writing and testing templates for all 15+ formats took two weeks. Every new telco promotion, new SMS layout, or seasonal format change can break a template. I now run the corpus through the parser on every commit (CI) and alert on any drop in coverage.

---

## Open source

The parser is MIT-licensed and available at [github.com/theboylexis/momo-parse-api](https://github.com/theboylexis/momo-parse-api).

```bash
pip install momoparse
```

```python
import parser as p
result = p.parse("Payment made for GHS 50.00 to DAVID BOATENG...")
print(result.amount)     # 50.0
print(result.tx_type)    # "transfer_sent"
print(result.confidence) # 0.97
```

The categorization model, enrichment analytics, and financial profiling layer sit on top of the open-source parser and are available via the [MomoParse API](https://web-production-5aa38.up.railway.app/docs) — free sandbox key included, no sign-up.

---

*Built in Accra. Questions and PRs welcome.*

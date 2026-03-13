# Cold Outreach Email Templates — Week 7

Target personas: fintech CTOs, lending platform engineers, MFI data teams, developer tool builders in Ghana/West Africa.

---

## Template A — Fintech / Lending Platform (Primary)

**Subject:** Structured MoMo data for [Company Name]'s underwriting

Hi [Name],

Quick one — I noticed [Company Name] does [loan origination / credit scoring / financial services] for mobile money users. Are you parsing MoMo SMS to assess transaction history?

We built MomoParse to solve exactly that. It takes raw MTN, Telecel, and AirtelTigo SMS and returns structured JSON — transaction type, amount, balance, counterparty, date — plus financial signals like income consistency, expense ratio, and business activity score.

Free sandbox key: `sk-sandbox-momoparse` — try it in 30 seconds:

```bash
curl -X POST https://web-production-5aa38.up.railway.app/v1/parse \
  -H "X-API-Key: sk-sandbox-momoparse" \
  -H "Content-Type: application/json" \
  -d '{"sms_text": "Payment received for GHS 500.00 from KWAME BOATENG..."}'
```

If you're building credit models on MoMo data, I'd like to show you the `/v1/profile` endpoint — it aggregates 1,000 SMS into a borrower profile in under a second.

Worth a 20-minute call?

[Your name]
MomoParse | hello@momoparse.com

---

## Template B — Developer / Technical Founder

**Subject:** Open-source MoMo SMS parser

Hi [Name],

Are you dealing with raw MoMo SMS in any of your projects?

I open-sourced a Python parser that handles 15+ MTN/Telecel/AirtelTigo formats — returns structured JSON with confidence scores. MIT licensed.

```python
pip install momoparse
result = p.parse(sms_text)
# → {tx_type, amount, balance, counterparty, date, confidence}
```

GitHub: [github.com/theboylexis/momo-parse-api](https://github.com/theboylexis/momo-parse-api)

The open-source part handles extraction. If you need categorization (rent vs. salary vs. merchant) or batch analytics, there's an API layer with a free sandbox.

Let me know if you hit any edge cases — always looking to improve template coverage.

[Your name]

---

## Template C — MFI / NGO (Non-technical decision maker)

**Subject:** Automated MoMo statement analysis for [Organization Name]

Hi [Name],

I work with microfinance teams in Ghana who need to assess clients' financial health from their MoMo history. The current process is usually manual — reviewing screenshots or asking clients to forward SMS.

We built a tool that automates this. Clients share their MoMo SMS (which they already have), and MomoParse returns:

- Total income and expenses over any period
- Spending categories (rent, transport, merchant payments, airtime)
- Business activity signals and irregular transaction alerts
- A borrower risk profile

It integrates via a simple API call — no app install required on the client side.

If this fits into your credit assessment or savings programme workflow, I'd be happy to walk through a demo with your team.

[Your name]
MomoParse | hello@momoparse.com

---

## Template D — Follow-up (After no response, Day 7)

**Subject:** Re: MoMo data for [Company Name]

Hi [Name],

Just bumping this in case it got buried. Short version:

MomoParse parses raw MoMo SMS → structured financial data. Free sandbox, no sign-up: `sk-sandbox-momoparse`.

If it's not relevant right now, no worries — happy to check back in a few months.

[Your name]

---

## Target list structure

| # | Company | Contact | Persona | Channel | Status |
|---|---------|---------|---------|---------|--------|
| 1 | | | | LinkedIn / Email | |
| 2 | | | | | |
| ... | | | | | |

**Where to find targets:**
- GhTech Slack (#fintech, #developers channels)
- DevCongress Ghana community
- LinkedIn search: "CTO Ghana fintech", "credit scoring Ghana", "mobile money API"
- Twitter/X: #GhTech, #AfricaFintech, #MoMo
- YC Africa batch companies
- i2i Fund / IFC portfolio companies operating in Ghana

**Outreach cadence:**
- Day 0: Send Template A or B
- Day 7: Send Template D if no response
- Day 14: Move to cold → deprioritized

**Goal for Week 7:** Contact 20 targets, book 3 demo calls.

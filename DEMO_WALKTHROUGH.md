# MomoParse Demo Walkthrough — Thursday Apr 10

Talking points for the demo with Michael (Backend, AmaliTech).

---

## 1. The Problem (1 min)

- Ghana has 74.6M registered mobile money wallets, 23.9M active
- GHS 1 trillion in Q1 2025 alone (up 74% YoY), on track for ~GHS 4T annually
- Telcos score users with proprietary algorithms the user never sees
- Credit scoring is an officially licensed FinTech activity (15% of 59 approved entities)
- **The inversion**: users generate the data, but telcos own the intelligence
- MomoParse extracts **6 of 8 telco credit scoring signals** from user-owned SMS data alone

## 2. Architecture Overview (2 min)

Walk through the 3-stage pipeline shown on the demo page:

```
Raw SMS → Parser (23 regex templates) → ML Categorizer (Random Forest) → Financial Indexes → JSON
```

**Key design decisions to mention:**
- **Rule-based parser, not LLM** — deterministic, fast (<5ms per SMS), no API costs, auditable
- **3-layer categorization** — rules first (high confidence), ML second, counterparty learning third
- **Academic grounding** — each of the 5 financial indexes cites a published paper (Lusardi & Mitchell, Gottschalk & Moffitt, etc.)
- **Template architecture** — adding a new SMS format is just a JSON object, no code changes

## 3. Live Demo (5 min)

### Step A: Single Parse (show the core)
1. Open `https://momo-parse.up.railway.app/demo`
2. Click **"Parse first SMS"**
3. Walk through the response fields:
   - `telco: "telecel"` — detected from SMS content
   - `tx_type: "transfer_received"` — matched template
   - `amount`, `balance`, `fee` — extracted via regex capture groups
   - `category: "wages_salary"` — ML categorized from "January salary" reference
   - `confidence: 0.9` — min(telco_confidence, template_confidence)
4. Show the raw JSON — "this is what integrators get back"

### Step B: Financial Report (show the value)
1. Click **"Generate report"** with the pre-loaded 10 sample SMS
2. Walk through:
   - **Health Score** (animated ring) — composite of 5 indexes
   - **KPIs** — total income, expenses, net savings, savings rate
   - **Monthly breakdown** — Jan vs Feb comparison with savings bars
   - **Financial Indexes** — savings rate, income stability, expense volatility, HHI, velocity
   - **Categories** — spending breakdown by category with horizontal bars
   - **Insights** — auto-generated spending observations
   - **Recommendations** — actionable budget advice

### Step C: Switch to MTN (show multi-telco)
1. Switch dropdown to "MTN MoMo" — sample SMS changes automatically
2. Generate report again — same pipeline, different telco templates
3. "Two telcos, 23 templates, ~95% of national MoMo volume covered"

### Step D: Swagger Docs (show the API)
1. Open `/docs` — custom Swagger UI
2. Show the 6 endpoints: parse, parse/batch, enrich, profile, report, jobs
3. "All protected by API key auth with tiered rate limiting"

## 4. Technical Depth (3 min — what Michael will care about)

### Backend Stack
- **FastAPI** with async endpoints
- **Pydantic** models for request/response validation
- **SQLAlchemy** for job persistence (PostgreSQL on Railway, SQLite fallback)
- **scikit-learn** Random Forest for categorization
- **Hypothesis** for property-based testing

### Engineering Highlights
- **543 tests** — unit, integration, property-based, and real SMS corpus
- **CI/CD** — GitHub Actions runs tests on push, publishes to PyPI on tags
- **Docker** deployment on Railway with auto-restart
- **Async job processing** — requests with 500+ SMS go to background queue
- **Rate limiting** — sliding window per tier (sandbox, free, starter)
- **Published on PyPI** — `pip install momoparse`

### Things You Did From Scratch
- The entire 3-stage parser pipeline
- 23 regex templates reverse-engineered from real MTN/Telecel SMS
- The ML categorizer with 406 hand-labeled training samples
- Financial health scoring formula with academic citations
- The Python SDK (sync + async clients)
- CI/CD pipeline and Docker deployment

## 5. What's Next (1 min)

- AirtelTigo template support (3rd telco)
- Redis-backed rate limiting for production scale
- Webhook retry logic with exponential backoff
- More training data for the ML categorizer
- Potential: mobile app that reads SMS directly

## Quick Reference

| Item | Value |
|------|-------|
| Live API | https://momo-parse.up.railway.app |
| Demo page | https://momo-parse.up.railway.app/demo |
| Swagger docs | https://momo-parse.up.railway.app/docs |
| GitHub | https://github.com/theboylexis/momo-parse-api |
| PyPI | https://pypi.org/project/momoparse/ |
| Sandbox key | `sk-sandbox-momoparse` |
| Tests | 543 passing |
| Templates | 23 (9 MTN, 14 Telecel) |

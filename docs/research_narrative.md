# Research Narrative — MomoParse

## 1. Problem Statement

Ghana's mobile money ecosystem processes over 8.1 billion transactions annually across 74.1 million registered wallets, with a total transaction value of GH¢3.01 trillion (Bank of Ghana, 2024 Full Year FinTech Sector Report). For most Ghanaians — particularly the 60% of adults 15+ who hold mobile money accounts — this is their primary financial infrastructure.

Yet a fundamental asymmetry exists: the telcos who operate these platforms — MTN Ghana (MoMo) and Telecel Ghana (Telecel Cash) — collect, analyze, and monetize user transaction data through proprietary systems, while the users who generate that data have no programmatic access to their own financial history.

This asymmetry has concrete consequences:

- **Credit scoring is opaque.** MTN's partnership with TransUnion deploys the CreditVision Telco Data Score, which determines Qwikloan eligibility (GH¢25–1,000) based on transaction history, recharge patterns, and behavioral signals. Users cannot see, challenge, or port this score.

- **Service access is determined by hidden algorithms.** XtraTime (airtime advance) limits are set by "loyalty and activeness on the network." Just4U bundle pricing is personalized based on ARPU and usage patterns. The criteria are not disclosed.

- **Financial visibility is limited.** Users can request transaction history via USSD or the telco apps for a subsidized fee, but these exports are raw transaction lists — not structured, categorized, or analyzable. There is no API for transaction history, no standardized data format, and no tools to derive financial insights from the data. The gap is not access to records, but access to *intelligence* derived from those records.

## 2. The Opportunity

Every mobile money transaction on the Ericsson Wallet Platform — which powers both MTN MoMo and Telecel Cash — generates a template-based SMS confirmation delivered to the user. These confirmations contain structured information: transaction type, amount, counterparty, date, balance, fees, and transaction ID.

The key insight is that **these SMS messages encode the same behavioral signals that telcos use for internal credit scoring**, but in a form that the user owns and controls. Specifically:

| Telco Internal Signal | SMS-Derivable Equivalent | Financial Meaning |
|----------------------|--------------------------|-------------------|
| Top-up frequency | Income transaction frequency | Income stability |
| Transaction volume | Total inflows/outflows | Cash flow capacity |
| Recharge consistency | Spending regularity patterns | Financial discipline |
| CDR contact diversity | Counterparty diversity | Economic activity breadth |
| Loan repayment history | Recurring payment detection | Creditworthiness |
| ARPU | Average transaction size | Economic tier |

Of the 8 key signals identified in telco credit scoring literature (Björkegren & Grissen, 2018), 6 can be approximated from SMS data alone. The two that cannot — location data and device behavior patterns — require invasive device-level access that contradicts the user-ownership thesis.

## 3. Regulatory Context

The Bank of Ghana regulates mobile money through a three-tier KYC structure (revised March 1, 2024):

| Tier | KYC Requirement | Daily Limit | Max Balance | Monthly Limit |
|------|----------------|-------------|-------------|---------------|
| Minimum | Ghana Card only | GH¢3,000 | GH¢5,000 | GH¢10,000 |
| Medium | + Next of kin, source of funds | GH¢15,000 | GH¢40,000 | Unlimited |
| Enhanced | + Proof of address | GH¢25,000 | GH¢75,000 | Unlimited |

The majority of mobile money users operate at the Minimum KYC tier — the segment with the least financial infrastructure and the most to gain from tools that provide financial visibility. These caps also have implications for financial index computation: transaction amounts and frequencies are bounded by regulatory constraints, which must be accounted for in scoring methodology.

Agent wallets operate on a separate tier structure (GH¢1M to unlimited), reflecting the commercial role of mobile money agents in the cash-in/cash-out ecosystem.

## 4. Competitive Landscape

The African open banking and financial data space has several active players, none of whom address the specific problem MomoParse targets:

| Player | Approach | Limitation |
|--------|----------|------------|
| Pngme ($18M raised) | Phone SDK reads SMS on-device | Requires app install, enterprise-only, opaque processing |
| Mono (Nigeria) | Bank API integration | Banks, not mobile money wallets |
| Stitch (South Africa) | Bank API integration | Same — no mobile money coverage |
| Okra (Nigeria) | Bank API integration | Ceased operations May 2025 |
| PawaPay / Tola | Payment aggregation APIs | Process payments, don't analyze history |
| MTN MoMo API (30 endpoints) | Transaction initiation | Forward-looking (make payments), not backward-looking (analyze history) |

MomoParse occupies an uncontested position: **a lightweight, developer-facing API that converts user-owned SMS data into structured financial intelligence, with no SDK install, no bank integration, and no proprietary data access required.**

## 5. Technical Approach

MomoParse is structured as a four-layer pipeline:

**Layer 1: Pattern-Based Parsing.** Regex-based extraction of transaction fields from MTN MoMo and Telecel Cash SMS templates. Each telco has distinct SMS formats for different transaction types (P2P transfers, merchant payments, cash withdrawals, airtime purchases, etc.). The parser identifies the telco, matches a template, and extracts structured fields.

**Layer 2: ML Categorization.** A RandomForest classifier assigns spending categories (e.g., merchant_payment, airtime_data, loan_repayment) based on features extracted from the parsed transaction: transaction type, amount bucket, counterparty keywords, and reference text. This layer is complemented by a counterparty learning system that improves classification over time.

**Layer 3: Financial Index Computation.** Five formalized indexes, each grounded in established financial methodology:

1. **Savings Rate** — (Income − Expenses) / Income. Standard personal finance metric (Lusardi & Mitchell, 2014).
2. **Transaction Velocity** — Transactions per day. Proxy for economic activity, analogous to CDR frequency in telco scoring (Björkegren & Grissen, 2018).
3. **Income Stability Index** — Coefficient of variation of monthly income. Standard volatility measure in labor economics (Gottschalk & Moffitt, 1994).
4. **Counterparty Concentration** — Herfindahl-Hirschman Index of transaction partners. Adapted from antitrust economics; low concentration signals diversified economic activity.
5. **Expense Volatility** — Normalized standard deviation of monthly spending. High volatility correlates with financial stress (Morduch & Schneider, 2017).

**Layer 4: Composite Scoring.** A weighted combination of the five indexes produces a 0–100 financial health score. Weights reflect relative importance for mobile money users: Savings Rate (30%), Income Stability (25%), Expense Volatility (20%), Counterparty Diversity (15%), Transaction Velocity (10%).

## 6. Thesis

In a market of 74 million wallets and GH¢3 trillion in annual transactions, telcos score users with proprietary algorithms the user never sees. MomoParse extracts the same financial signals from user-owned SMS data — transparently, through an open API — giving users and developers access to financial intelligence that was previously locked inside telco systems.

## References

- Bank of Ghana. (2024). *FinTech Sector Report 2024 Full Year.* https://www.bog.gov.gh
- Björkegren, D., & Grissen, D. (2018). *Behavior Revealed in Mobile Phone Usage Predicts Credit Repayment.* The World Bank Economic Review, 34(3), 618–634.
- Gottschalk, P., & Moffitt, R. (1994). *The Growth of Earnings Instability in the U.S. Labor Market.* Brookings Papers on Economic Activity, 1994(2), 217–272.
- Lusardi, A., & Mitchell, O. S. (2014). *The Economic Importance of Financial Literacy: Theory and Evidence.* Journal of Economic Literature, 52(1), 5–44.
- Morduch, J., & Schneider, R. (2017). *The Financial Diaries: How American Families Cope in a World of Uncertainty.* Princeton University Press.
- Hirschman, A. O. (1964). *The Paternity of an Index.* The American Economic Review, 54(5), 761–762.
- Ericsson. (2022). *The Six Axes Evolution of Mobile Money — Part 2.* https://www.ericsson.com/en/blog/2022/12/mobile-moneysix-ways-in-which-the-ecosystem-is-evolving-part2

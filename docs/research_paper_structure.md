# Research Paper Structure — MomoParse

**Working Title:** *User-Owned Financial Intelligence from Mobile Money SMS: A Lightweight Approach to Transaction Categorization and Financial Scoring in Ghana*

---

## 1. Abstract
- Problem: telco data asymmetry in Ghana's mobile money ecosystem
- Approach: SMS parsing + ML categorization + composite financial index
- Key result: 6 of 8 telco scoring signals recovered from user-owned data alone

## 2. Introduction
- Ghana's mobile money scale (74.1M wallets, GHS 3.01T)
- Telcos score users with proprietary algorithms users can't see
- Research question: *Can user-owned SMS confirmations provide equivalent financial intelligence without proprietary access?*

## 3. Related Work
- Telco credit scoring: TransUnion CreditVision, Björkegren & Grissen (2018)
- Alternative credit scoring in emerging markets: Pngme, Mono, Okra
- Financial literacy & savings measurement: Lusardi & Mitchell (2014)
- Income volatility: Gottschalk & Moffitt (1994), Morduch & Schneider (2017)
- Market concentration: Hirschman (1964) HHI

## 4. System Architecture
- SMS template infrastructure (Ericsson Wallet Platform → SMSC → phone)
- Parser layer: 23 regex templates, branded/unbranded deduplication
- 3-layer categorization pipeline: rules → ML → counterparty learning
- Financial enrichment layer

## 5. ML Categorization Model
- Feature engineering: 44 features (amount bucket, tx type one-hot, keyword indicators, presence flags)
- Model selection rationale: RF vs. LR vs. XGBoost vs. MLP vs. NB
- Training: 406 samples, 15 categories, `class_weight="balanced"`
- Feature importance analysis (top 10)
- **Honest limitations** — no held-out test, CV impossible, class imbalance, corpus bias

## 6. Financial Health Index (MFH)

### Unified formula

$$H = 100 \sum_{i=1}^{5} w_i \cdot \hat{x}_i$$

where:

$$\hat{x}_i = \text{clamp}_{[0,1]}\left(\frac{x_i - x_i^{\min}}{x_i^{\max} - x_i^{\min}}\right)$$

### Sub-indexes

| Index | Formula | Weight | Citation |
|-------|---------|--------|----------|
| Savings Rate (S) | (Income − Expenses) / Income | 30% | Lusardi & Mitchell (2014) |
| Income Stability (V_I) | σ(monthly income) / μ(monthly income) | 25% | Gottschalk & Moffitt (1994) |
| Expense Volatility (V_E) | σ(monthly expense) / μ(monthly expense) | 20% | Morduch & Schneider (2017) |
| Counterparty Concentration (C) | Σ(share_i²) | 15% | Hirschman (1964) |
| Transaction Velocity (T) | transactions / days | 10% | Björkegren & Grissen (2018) |

### Expanded form

$$H = 100\left[0.30\,\hat{S} + 0.25\,(1 - \hat{V}_I) + 0.20\,(1 - \hat{V}_E) + 0.15\,(1 - C_{\text{HHI}}) + 0.10\,\hat{T}\right]$$

The (1 − x) terms invert "bad-is-high" indexes so higher always means healthier.

### Signal mapping to telco scoring (6 of 8)

| Telco Signal (Internal) | MomoParse (From SMS) | Status |
|--------------------------|----------------------|--------|
| Top-up frequency | Income txn frequency | Captured |
| Transaction volume | Total inflows/outflows | Captured |
| Recharge consistency | Spending regularity | Captured |
| CDR contact diversity | Counterparty diversity | Captured |
| Loan repayment history | Recurring payment patterns | Captured |
| ARPU | Avg transaction size | Captured |
| Location data | *Not available* | Missing — requires invasive access |
| Battery/device habits | *Not available* | Missing — requires invasive access |

### Low-data penalty
When fewer than 2 months of data are available, a −10 penalty is applied and the score is capped at 70.

## 7. Validation
- 543 automated tests
- 100 real Telecel transactions validated against official statement
- 80+ real MTN transactions from SMS
- 27 statement transaction types mapped
- Duplicate SMS discovery (branded + unbranded)

## 8. Discussion
- What MomoParse can vs. cannot capture (2 missing signals: location, device)
- Competitive landscape positioning (lightweight + developer-friendly quadrant)
- Privacy tradeoff: transparency vs. invasiveness
- Limitations: single-corpus bias, small labeled dataset, no production deployment yet

## 9. Future Work
- Data collection targets (1000+ samples, proper cross-validation)
- Model benchmarking (Logistic Regression, Naive Bayes baselines)
- Confidence calibration for predict_proba outputs
- Continuous learning from user corrections
- Potential for portable credit profiles

## 10. Conclusion

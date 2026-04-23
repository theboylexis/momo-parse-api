# MFH Weight Sensitivity Analysis

Perturbs each of the five MFH sub-index weights by ±0.10 (redistributing across the remaining weights to maintain Σw = 1) and reports the resulting composite score change across 6 canonical user profiles that span the sub-score space.

## Published weights

| Sub-index | Weight |
|---|---:|
| savings_rate | 0.30 |
| income_stability | 0.25 |
| expense_volatility | 0.20 |
| counterparty_concentration | 0.15 |
| transaction_velocity | 0.10 |

## Per-profile results

### High saver, diversified
_Strong savings, stable income, many counterparties_

- Baseline composite: **87.4**

| Weight perturbed | −0.10 | +0.10 | Max |Δ| |
|---|---:|---:|---:|
| savings_rate | 87.4 | 87.4 | 0.0 |
| income_stability | 87.3 | 87.5 | 0.1 |
| expense_volatility | 88.1 | 86.7 | 0.7 |
| counterparty_concentration | 87.7 | 87.1 | 0.3 |
| transaction_velocity | 86.0 | 88.8 | 1.4 |

### Negative saver, concentrated
_Spending exceeds income, one dominant counterparty_

- Baseline composite: **32.4**

| Weight perturbed | −0.10 | +0.10 | Max |Δ| |
|---|---:|---:|---:|
| savings_rate | 34.3 | 30.4 | 1.9 |
| income_stability | 31.4 | 33.4 | 1.0 |
| expense_volatility | 30.8 | 34.0 | 1.6 |
| counterparty_concentration | 33.2 | 31.5 | 0.9 |
| transaction_velocity | 31.5 | 33.2 | 0.8 |

### Volatile trader
_Modest savings but high income and expense volatility_

- Baseline composite: **43.2**

| Weight perturbed | −0.10 | +0.10 | Max |Δ| |
|---|---:|---:|---:|
| savings_rate | 41.9 | 44.6 | 1.3 |
| income_stability | 47.0 | 39.5 | 3.8 |
| expense_volatility | 46.2 | 40.3 | 2.9 |
| counterparty_concentration | 40.7 | 45.8 | 2.6 |
| transaction_velocity | 36.9 | 49.6 | 6.3 |

### Salaried, low activity
_Steady income, few transactions, concentrated payees_

- Baseline composite: **66.5**

| Weight perturbed | −0.10 | +0.10 | Max |Δ| |
|---|---:|---:|---:|
| savings_rate | 66.7 | 66.3 | 0.2 |
| income_stability | 63.1 | 69.9 | 3.4 |
| expense_volatility | 65.4 | 67.6 | 1.1 |
| counterparty_concentration | 69.6 | 63.4 | 3.1 |
| transaction_velocity | 70.6 | 62.4 | 4.1 |

### Micro-merchant
_Moderate savings, high tx velocity, diverse customers_

- Baseline composite: **68.2**

| Weight perturbed | −0.10 | +0.10 | Max |Δ| |
|---|---:|---:|---:|
| savings_rate | 69.4 | 67.1 | 1.2 |
| income_stability | 68.7 | 67.8 | 0.4 |
| expense_volatility | 69.3 | 67.2 | 1.0 |
| counterparty_concentration | 66.9 | 69.6 | 1.4 |
| transaction_velocity | 64.7 | 71.8 | 3.5 |

### Thin file
_Near-zero savings, minimal activity_

- Baseline composite: **44.8**

| Weight perturbed | −0.10 | +0.10 | Max |Δ| |
|---|---:|---:|---:|
| savings_rate | 45.4 | 44.1 | 0.7 |
| income_stability | 43.4 | 46.1 | 1.4 |
| expense_volatility | 44.1 | 45.4 | 0.7 |
| counterparty_concentration | 44.1 | 45.4 | 0.6 |
| transaction_velocity | 48.1 | 41.4 | 3.3 |

## Summary — worst-case swing per weight (across all profiles)

| Weight | Published w | Max |Δ composite| under ±0.10 |
|---|---:|---:|
| savings_rate | 0.30 | 1.9 pp |
| income_stability | 0.25 | 3.8 pp |
| expense_volatility | 0.20 | 2.9 pp |
| counterparty_concentration | 0.15 | 3.1 pp |
| transaction_velocity | 0.10 | 6.3 pp |

**Overall worst case:** a single ±0.10 weight shift moves the composite by at most **6.3 points** on any tested profile. The published 30/25/20/15/10 weighting is robust to moderate weight revisions — small disagreements in the exact weight values do not materially change the score.

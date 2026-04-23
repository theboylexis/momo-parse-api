================================================================
 MOMOPARSE — FINANCIAL HEALTH REPORT (end-to-end demo)
================================================================

SMS messages read from export:       2724
Parsed as valid transactions:        2020
Data confidence:                     high
Date range covered:                  2022-10-17 → 2026-04-22
Months of activity:                  43

----------------------------------------------------------------
 FINANCIAL HEALTH SCORE:  27 / 100
----------------------------------------------------------------

What's driving the score:

  transaction_velocity            contributes  10 pts  (normalized 1.00)
  counterparty_concentration      contributes   9 pts  (normalized 0.58)
  savings_rate                    contributes   8 pts  (normalized 0.27)
  income_stability                contributes   0 pts  (normalized 0.00)
  expense_volatility              contributes   0 pts  (normalized 0.00)

Cash flow:
  Total income:         GHS 973,249.17
  Total expenses:     GHS 1,051,975.82
  Net:                  GHS -78,726.65
  Savings rate:                  -8.1 %

Top categories by amount:
  personal_transfer_received     GHS 924,938.79 (345 tx)   █████████████···············
  merchant_payment               GHS 781,866.00 (196 tx)   ███████████·················
  personal_transfer_sent         GHS 181,051.50 (753 tx)   ███·························
  utilities                       GHS 81,704.32 (314 tx)   █···························
  cash_deposit                    GHS 44,586.38 (278 tx)   █···························
  cash_withdrawal                  GHS 3,241.00 (13 tx)   ····························
  uncategorized                    GHS 2,793.30 (66 tx)   ····························
  rent                             GHS 1,875.00 (3 tx)   ····························

Monthly timeline (last 12 months shown):
  2025-05  income   GHS 3,322.38  expense   GHS 3,314.29  savings   0.2%
  2025-06  income   GHS 1,811.00  expense   GHS 3,122.50  savings -72.4%
  2025-07  income   GHS 2,968.00  expense   GHS 3,280.82  savings -10.5%
  2025-08  income   GHS 2,671.00  expense   GHS 2,139.00  savings  19.9%
  2025-09  income   GHS 1,195.00  expense   GHS 1,632.50  savings -36.6%
  2025-10  income     GHS 994.00  expense     GHS 889.00  savings  10.6%
  2025-11  income   GHS 2,245.00  expense   GHS 5,098.07  savings -127.1%
  2025-12  income   GHS 2,459.00  expense   GHS 1,471.16  savings  40.2%
  2026-01  income   GHS 1,792.20  expense   GHS 3,685.63  savings -105.6%
  2026-02  income   GHS 3,818.79  expense   GHS 5,866.50  savings -53.6%
  2026-03  income   GHS 1,150.50  expense   GHS 2,243.00  savings -95.0%
  2026-04  income   GHS 2,880.00  expense   GHS 3,085.00  savings  -7.1%

Insights:
  - Biggest expense category: Merchant Payment accounts for 38.6% of your total transaction volume (GHS 781,866.00).
  - Month-over-month spending: Your spending increased by 37.5% from 2026-03 (GHS 2,243.00) to 2026-04 (GHS 3,085.00).

Recommendations:
  - Boost your savings rate: Your savings rate is -8.1%. Aim for at least 10-20% by cutting discretionary spending.
  - Review merchant payment spending: Merchant Payment is 74.3% of your total expenses. Look for ways to optimize or negotiate better rates.

================================================================
 HOW TO READ THIS
================================================================

The score is 0-100 — higher is 'healthier'. Think of it as a
credit-risk proxy: a lender seeing 70+ has evidence of regular
income, stable spending, and reasonable savings; 40 or below
means the pattern of transactions looks volatile or cash-poor.

The five drivers above decompose that number. Each sub-index is
normalized to [0, 1] and multiplied by its weight, then summed
to 100. The top driver is the strongest reason the score is
where it is; the bottom driver is the main thing to improve.

Data confidence tells the lender how much to trust the score.
Less than 3 months of data → confidence drops fast.

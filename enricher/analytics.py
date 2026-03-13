"""
Aggregate analytics computed from a list of parsed+categorized transactions.

Used by both /v1/enrich and /v1/profile.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any, Optional


# ── Income vs expense classification ─────────────────────────────────────────

_INCOME_CATEGORIES = {
    "sales_revenue",
    "personal_transfer_received",
    "loan_disbursement",
    "wages_salary",
    "cash_deposit",
}

_EXPENSE_CATEGORIES = {
    "supplier_payment",
    "merchant_payment",
    "personal_transfer_sent",
    "airtime_data",
    "utilities",
    "rent",
    "transport",
    "loan_repayment",
    "cash_withdrawal",
    "fee_charge",
}


def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except ValueError:
            continue
    return None


def compute_summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute aggregate analytics from a list of parsed transaction dicts.

    Each dict should have: amount, category, counterparty_name,
    counterparty_phone, date, category_confidence.
    """
    total_income = 0.0
    total_expenses = 0.0
    category_amounts: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    counterparties: set[str] = set()
    dates: list[date] = []

    for tx in transactions:
        amount = tx.get("amount") or 0.0
        category = tx.get("category") or "uncategorized"

        if category in _INCOME_CATEGORIES:
            total_income += amount
        elif category in _EXPENSE_CATEGORIES:
            total_expenses += amount

        category_amounts[category] += amount
        category_counts[category] += 1

        # Counterparty tracking
        cp = tx.get("counterparty_phone") or tx.get("counterparty_name")
        if cp:
            counterparties.add(cp.strip().upper())

        # Date tracking
        d = _parse_date(tx.get("date"))
        if d:
            dates.append(d)

    net_cash_flow = total_income - total_expenses
    total_amount = sum(category_amounts.values()) or 1.0

    # Category breakdown
    category_breakdown: dict[str, dict] = {}
    for cat, amt in category_amounts.items():
        category_breakdown[cat] = {
            "amount": round(amt, 2),
            "count": category_counts[cat],
            "percentage": round(amt / total_amount * 100, 1),
        }

    # Date range & frequency
    date_range: dict[str, Any] = {"start": None, "end": None, "days_covered": 0}
    tx_frequency_per_day = 0.0
    if dates:
        start, end = min(dates), max(dates)
        days = max((end - start).days, 1)
        date_range = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days_covered": days,
        }
        tx_frequency_per_day = round(len(transactions) / days, 2)

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "transaction_count": len(transactions),
        "category_breakdown": category_breakdown,
        "transaction_frequency_per_day": tx_frequency_per_day,
        "unique_counterparties": len(counterparties),
        "date_range": date_range,
    }


def compute_profile(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute a higher-level financial profile for credit scoring / lending use cases.
    """
    summary = compute_summary(transactions)

    # ── Monthly income breakdown ──────────────────────────────────────────────
    monthly_income: dict[str, float] = defaultdict(float)
    monthly_expense: dict[str, float] = defaultdict(float)

    for tx in transactions:
        amount = tx.get("amount") or 0.0
        category = tx.get("category") or "uncategorized"
        d = _parse_date(tx.get("date"))
        if d:
            month_key = d.strftime("%Y-%m")
            if category in _INCOME_CATEGORIES:
                monthly_income[month_key] += amount
            elif category in _EXPENSE_CATEGORIES:
                monthly_expense[month_key] += amount

    income_values = list(monthly_income.values())
    avg_monthly_income = round(statistics.mean(income_values), 2) if income_values else 0.0

    # Income consistency: coefficient of variation (lower = more consistent)
    if len(income_values) >= 2 and avg_monthly_income > 0:
        income_cv = round(statistics.stdev(income_values) / avg_monthly_income, 3)
    else:
        income_cv = 0.0

    # Expense ratio
    total_income = summary["total_income"]
    total_expenses = summary["total_expenses"]
    expense_ratio = round(total_expenses / total_income, 3) if total_income > 0 else 0.0

    # ── Top 5 counterparties by transaction volume ────────────────────────────
    cp_amounts: dict[str, float] = defaultdict(float)
    cp_counts: dict[str, int] = defaultdict(int)

    for tx in transactions:
        cp = tx.get("counterparty_phone") or tx.get("counterparty_name")
        if cp:
            key = cp.strip().upper()
            cp_amounts[key] += tx.get("amount") or 0.0
            cp_counts[key] += 1

    top_counterparties = [
        {
            "identifier": cp,
            "total_amount": round(amt, 2),
            "transaction_count": cp_counts[cp],
        }
        for cp, amt in sorted(cp_amounts.items(), key=lambda x: -x[1])[:5]
    ]

    # ── Business activity score (0–100) ──────────────────────────────────────
    # Signals: merchant_payment inflow, high tx frequency, multiple counterparties,
    # presence of sales_revenue
    score = 0
    cb = summary["category_breakdown"]

    if "sales_revenue" in cb:
        score += 30
    if "merchant_payment" in cb:
        score += 15
    if summary["unique_counterparties"] >= 10:
        score += 20
    elif summary["unique_counterparties"] >= 5:
        score += 10
    if summary["transaction_frequency_per_day"] >= 2:
        score += 20
    elif summary["transaction_frequency_per_day"] >= 0.5:
        score += 10
    if len(income_values) >= 3:
        score += 15  # sustained activity over multiple months

    business_activity_score = min(score, 100)

    # ── Revenue trend ─────────────────────────────────────────────────────────
    revenue_trend = "stable"
    if len(income_values) >= 3:
        first_half = statistics.mean(income_values[: len(income_values) // 2])
        second_half = statistics.mean(income_values[len(income_values) // 2 :])
        if second_half > first_half * 1.10:
            revenue_trend = "growing"
        elif second_half < first_half * 0.90:
            revenue_trend = "declining"

    # ── Risk signals ──────────────────────────────────────────────────────────
    risk_signals: list[dict] = []

    # Large irregular transactions (> 3x average)
    amounts = [tx.get("amount") or 0.0 for tx in transactions if tx.get("amount")]
    if amounts:
        avg_amount = statistics.mean(amounts)
        large_txs = [a for a in amounts if a > avg_amount * 3]
        if large_txs:
            risk_signals.append({
                "signal": "large_irregular_transactions",
                "description": f"{len(large_txs)} transaction(s) are >3x the average amount",
                "severity": "medium",
            })

    # Sudden drop in activity
    if len(income_values) >= 3:
        last = income_values[-1]
        prev_avg = statistics.mean(income_values[:-1])
        if prev_avg > 0 and last < prev_avg * 0.40:
            risk_signals.append({
                "signal": "sudden_income_drop",
                "description": "Last month income is <40% of prior average",
                "severity": "high",
            })

    # High expense ratio
    if expense_ratio > 0.90:
        risk_signals.append({
            "signal": "high_expense_ratio",
            "description": f"Expenses are {expense_ratio*100:.0f}% of income",
            "severity": "medium",
        })

    # High loan repayment burden
    loan_repayment_pct = cb.get("loan_repayment", {}).get("percentage", 0)
    if loan_repayment_pct > 20:
        risk_signals.append({
            "signal": "high_loan_burden",
            "description": f"Loan repayments are {loan_repayment_pct:.1f}% of total spend",
            "severity": "high",
        })

    return {
        "avg_monthly_income": avg_monthly_income,
        "income_consistency_cv": income_cv,
        "expense_ratio": expense_ratio,
        "top_counterparties": top_counterparties,
        "business_activity_score": business_activity_score,
        "revenue_trend": revenue_trend,
        "risk_signals": risk_signals,
        "months_of_data": len(income_values),
        "summary": summary,
    }

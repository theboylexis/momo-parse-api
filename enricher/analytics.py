"""
Aggregate analytics computed from a list of parsed+categorized transactions.

Used by both /v1/enrich and /v1/profile.

Financial indexes are grounded in established methodology:
- Savings Rate: standard personal finance metric (Lusardi & Mitchell, 2014)
- Transaction Velocity: proxy for economic activity, analogous to CDR frequency
  used in telco credit scoring (Björkegren & Grissen, 2018)
- Income Stability Index: coefficient of variation — standard measure of income
  volatility in labor economics (Gottschalk & Moffitt, 1994)
- Counterparty Concentration: Herfindahl-Hirschman Index adapted for transaction
  partners — low concentration signals diversified economic activity
- Expense Volatility: normalized standard deviation of monthly spending —
  high volatility correlates with financial stress (Morduch & Schneider, 2017)
"""
from __future__ import annotations

import math
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

# Fallback: classify by tx_type when category is uncategorized
_INCOME_TX_TYPES = {
    "transfer_received",
    "payment_received",
    "cash_deposit",
    "reversal_credit",
}

_EXPENSE_TX_TYPES = {
    "transfer_sent",
    "payment_sent",
    "cash_out",
    "cash_withdrawal",
    "airtime_purchase",
    "merchant_payment",
    "bill_payment",
}


def _is_income(tx: dict[str, Any]) -> bool:
    category = tx.get("category") or "uncategorized"
    if category in _INCOME_CATEGORIES:
        return True
    if category == "uncategorized":
        return (tx.get("tx_type") or "").lower() in _INCOME_TX_TYPES
    return False


def _is_expense(tx: dict[str, Any]) -> bool:
    category = tx.get("category") or "uncategorized"
    if category in _EXPENSE_CATEGORIES:
        return True
    if category == "uncategorized":
        return (tx.get("tx_type") or "").lower() in _EXPENSE_TX_TYPES
    return False


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

        if _is_income(tx):
            total_income += amount
        elif _is_expense(tx):
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
        d = _parse_date(tx.get("date"))
        if d:
            month_key = d.strftime("%Y-%m")
            if _is_income(tx):
                monthly_income[month_key] += amount
            elif _is_expense(tx):
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

    # Tiered: reward more transactions, not just presence
    sales_count = cb.get("sales_revenue", {}).get("count", 0)
    if sales_count >= 3:
        score += 30
    elif sales_count >= 1:
        score += 15

    merchant_count = cb.get("merchant_payment", {}).get("count", 0)
    if merchant_count >= 3:
        score += 15
    elif merchant_count >= 1:
        score += 8
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

    # ── Data confidence ────────────────────────────────────────────────────
    # Lets API consumers know how much to trust the scores
    total_tx = summary["transaction_count"]
    num_months = len(income_values)
    if num_months >= 3 and total_tx >= 20:
        data_confidence = "high"
    elif num_months >= 2 or total_tx >= 5:
        data_confidence = "medium"
    else:
        data_confidence = "low"

    # ── Formalized financial indexes ──────────────────────────────────────────
    financial_indexes = compute_financial_indexes(transactions)

    return {
        "avg_monthly_income": avg_monthly_income,
        "income_consistency_cv": income_cv,
        "expense_ratio": expense_ratio,
        "top_counterparties": top_counterparties,
        "business_activity_score": business_activity_score,
        "revenue_trend": revenue_trend,
        "risk_signals": risk_signals,
        "months_of_data": len(income_values),
        "data_confidence": data_confidence,
        "financial_indexes": financial_indexes,
        "summary": summary,
    }


# ── Monthly report ────────────────────────────────────────────────────────────


def compute_report(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Generate a monthly financial report with spending insights, savings
    analysis, and budget recommendations from parsed+categorized transactions.
    """
    summary = compute_summary(transactions)

    # ── Group transactions by month ──────────────────────────────────────────
    monthly_income: dict[str, float] = defaultdict(float)
    monthly_expense: dict[str, float] = defaultdict(float)
    monthly_counts: dict[str, int] = defaultdict(int)
    monthly_category_amounts: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    # First pass: bucket dated transactions and collect undated ones
    undated: list[dict[str, Any]] = []
    for tx in transactions:
        amount = tx.get("amount") or 0.0
        category = tx.get("category") or "uncategorized"
        d = _parse_date(tx.get("date"))
        if d:
            mk = d.strftime("%Y-%m")
            monthly_counts[mk] += 1
            if _is_income(tx):
                monthly_income[mk] += amount
            elif _is_expense(tx):
                monthly_expense[mk] += amount
            monthly_category_amounts[mk][category] += amount
        elif amount > 0:
            undated.append(tx)

    # Second pass: distribute undated transactions evenly across known months,
    # or into a single "undated" bucket if no dated transactions exist
    all_months = sorted(set(monthly_income) | set(monthly_expense) | set(monthly_counts))
    if undated and all_months:
        per_month = len(all_months)
        for tx in undated:
            amount = tx.get("amount") or 0.0
            category = tx.get("category") or "uncategorized"
            share = round(amount / per_month, 2)
            for mk in all_months:
                monthly_counts[mk] += 1
                if _is_income(tx):
                    monthly_income[mk] += share
                elif _is_expense(tx):
                    monthly_expense[mk] += share
                monthly_category_amounts[mk][category] += share
    elif undated:
        # No dated transactions at all — single bucket
        mk = "undated"
        for tx in undated:
            amount = tx.get("amount") or 0.0
            category = tx.get("category") or "uncategorized"
            monthly_counts[mk] += 1
            if _is_income(tx):
                monthly_income[mk] += amount
            elif _is_expense(tx):
                monthly_expense[mk] += amount
            monthly_category_amounts[mk][category] += amount
        all_months = [mk]

    all_months = sorted(set(monthly_income) | set(monthly_expense) | set(monthly_counts))
    month_breakdowns: list[dict[str, Any]] = []
    for mk in all_months:
        inc = round(monthly_income.get(mk, 0.0), 2)
        exp = round(monthly_expense.get(mk, 0.0), 2)
        net = round(inc - exp, 2)
        savings_rate = round(net / inc * 100, 1) if inc > 0 else 0.0
        month_breakdowns.append({
            "month": mk,
            "income": inc,
            "expenses": exp,
            "net_savings": net,
            "savings_rate": savings_rate,
            "transaction_count": monthly_counts.get(mk, 0),
        })

    # ── Spending insights ────────────────────────────────────────────────────
    insights: list[dict[str, str]] = []
    cb = summary["category_breakdown"]

    # Find top spending category (expense only)
    expense_cats = {
        cat: info for cat, info in cb.items() if cat in _EXPENSE_CATEGORIES
    }
    if expense_cats:
        top_cat = max(expense_cats, key=lambda c: expense_cats[c]["amount"])
        top_amt = expense_cats[top_cat]["amount"]
        top_pct = expense_cats[top_cat]["percentage"]
        insights.append({
            "type": "top_spending",
            "title": "Biggest expense category",
            "detail": (
                f"{_label(top_cat)} accounts for {top_pct}% of your total "
                f"transaction volume (GHS {top_amt:,.2f})."
            ),
        })

    # Month-over-month spending change
    if len(month_breakdowns) >= 2:
        prev, curr = month_breakdowns[-2], month_breakdowns[-1]
        if prev["expenses"] > 0:
            change_pct = round(
                (curr["expenses"] - prev["expenses"]) / prev["expenses"] * 100, 1
            )
            direction = "increased" if change_pct > 0 else "decreased"
            insights.append({
                "type": "spending_trend",
                "title": "Month-over-month spending",
                "detail": (
                    f"Your spending {direction} by {abs(change_pct)}% from "
                    f"{prev['month']} (GHS {prev['expenses']:,.2f}) to "
                    f"{curr['month']} (GHS {curr['expenses']:,.2f})."
                ),
            })

    # High fee alert
    fee_info = cb.get("fee_charge")
    if fee_info and fee_info["amount"] > 0:
        insights.append({
            "type": "fee_alert",
            "title": "Transaction fees",
            "detail": (
                f"You paid GHS {fee_info['amount']:,.2f} in fees across "
                f"{fee_info['count']} transaction(s). "
                "Consider consolidating transfers to reduce fees."
            ),
        })

    # Airtime/data spending
    airtime_info = cb.get("airtime_data")
    if airtime_info and summary["total_expenses"] > 0:
        airtime_pct = round(
            airtime_info["amount"] / summary["total_expenses"] * 100, 1
        )
        if airtime_pct > 10:
            insights.append({
                "type": "airtime_alert",
                "title": "High airtime & data spending",
                "detail": (
                    f"Airtime & data makes up {airtime_pct}% of your expenses "
                    f"(GHS {airtime_info['amount']:,.2f}). "
                    "A bundled plan could save you money."
                ),
            })

    # ── Savings analysis ─────────────────────────────────────────────────────
    total_income = summary["total_income"]
    total_expenses = summary["total_expenses"]
    net_savings = round(total_income - total_expenses, 2)
    overall_savings_rate = round(net_savings / total_income * 100, 1) if total_income > 0 else 0.0

    savings_analysis = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_savings": net_savings,
        "savings_rate": overall_savings_rate,
    }

    # ── Budget recommendations ───────────────────────────────────────────────
    recommendations: list[dict[str, str]] = []

    if overall_savings_rate < 10:
        recommendations.append({
            "priority": "high",
            "title": "Boost your savings rate",
            "detail": (
                f"Your savings rate is {overall_savings_rate}%. "
                "Aim for at least 10-20% by cutting discretionary spending."
            ),
        })
    elif overall_savings_rate >= 20:
        recommendations.append({
            "priority": "info",
            "title": "Strong savings habit",
            "detail": (
                f"You're saving {overall_savings_rate}% of your income — great job! "
                "Consider putting excess savings into a high-yield account or investment."
            ),
        })

    # Recommend reducing top expense if it's > 40% of expenses
    if expense_cats:
        top_cat = max(expense_cats, key=lambda c: expense_cats[c]["amount"])
        top_expense_pct = round(
            expense_cats[top_cat]["amount"] / total_expenses * 100, 1
        ) if total_expenses > 0 else 0.0
        if top_expense_pct > 40:
            recommendations.append({
                "priority": "medium",
                "title": f"Review {_label(top_cat).lower()} spending",
                "detail": (
                    f"{_label(top_cat)} is {top_expense_pct}% of your total expenses. "
                    "Look for ways to optimize or negotiate better rates."
                ),
            })

    # Loan burden warning
    loan_info = cb.get("loan_repayment")
    if loan_info and total_income > 0:
        loan_pct = round(loan_info["amount"] / total_income * 100, 1)
        if loan_pct > 15:
            recommendations.append({
                "priority": "high",
                "title": "High loan repayment burden",
                "detail": (
                    f"Loan repayments consume {loan_pct}% of your income "
                    f"(GHS {loan_info['amount']:,.2f}). "
                    "Prioritize paying down high-interest debt."
                ),
            })

    # ── Financial indexes & health score ──────────────────────────────────────
    financial_indexes = compute_financial_indexes(transactions)
    health_score = financial_indexes["composite_health_score"]

    # Data confidence
    total_tx = summary["transaction_count"]
    num_months = len(monthly_income)
    if num_months >= 3 and total_tx >= 20:
        data_confidence = "high"
    elif num_months >= 2 or total_tx >= 5:
        data_confidence = "medium"
    else:
        data_confidence = "low"

    return {
        "summary": summary,
        "months": month_breakdowns,
        "insights": insights,
        "savings_analysis": savings_analysis,
        "recommendations": recommendations,
        "financial_health_score": health_score,
        "financial_indexes": financial_indexes,
        "data_confidence": data_confidence,
    }


def compute_financial_indexes(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute five formalized financial indexes from parsed transactions.

    Each index maps to a known telco credit scoring signal and is grounded
    in established financial methodology.

    Returns a dict with each index value and a composite health score.
    """
    # ── Gather per-month and per-counterparty data ─────────────────────────
    monthly_income: dict[str, float] = defaultdict(float)
    monthly_expense: dict[str, float] = defaultdict(float)
    cp_amounts: dict[str, float] = defaultdict(float)
    dates: list[date] = []

    for tx in transactions:
        amount = tx.get("amount") or 0.0
        d = _parse_date(tx.get("date"))
        if d:
            mk = d.strftime("%Y-%m")
            dates.append(d)
            if _is_income(tx):
                monthly_income[mk] += amount
            elif _is_expense(tx):
                monthly_expense[mk] += amount

        cp = tx.get("counterparty_phone") or tx.get("counterparty_name")
        if cp:
            cp_amounts[cp.strip().upper()] += amount

    total_income = sum(monthly_income.values())
    total_expenses = sum(monthly_expense.values())
    income_values = list(monthly_income.values())
    expense_values = list(monthly_expense.values())

    # ── 1. Savings Rate (%) ────────────────────────────────────────────────
    # Standard: (Income - Expenses) / Income × 100
    # Reference: Lusardi & Mitchell (2014), financial literacy literature
    savings_rate = (
        round((total_income - total_expenses) / total_income * 100, 2)
        if total_income > 0
        else 0.0
    )

    # ── 2. Transaction Velocity (txns/day) ─────────────────────────────────
    # Proxy for economic activity — maps to telco CDR frequency
    # Reference: Björkegren & Grissen (2018), mobile phone credit scoring
    if dates:
        days = max((max(dates) - min(dates)).days, 1)
        tx_velocity = round(len(transactions) / days, 3)
    else:
        tx_velocity = 0.0

    # ── 3. Income Stability Index (0–1, lower = more stable) ───────────────
    # Coefficient of variation of monthly income
    # Reference: Gottschalk & Moffitt (1994), income volatility measurement
    if len(income_values) >= 2 and statistics.mean(income_values) > 0:
        income_stability = round(
            statistics.stdev(income_values) / statistics.mean(income_values), 3
        )
    else:
        income_stability = 0.0  # insufficient data

    # ── 4. Counterparty Concentration (HHI, 0–1) ──────────────────────────
    # Herfindahl-Hirschman Index: sum of squared market shares
    # 1.0 = all transactions with one counterparty (concentrated)
    # →0 = evenly distributed across many (diversified)
    # Reference: adapted from antitrust economics (Hirschman, 1964)
    total_cp_amount = sum(cp_amounts.values())
    if total_cp_amount > 0 and len(cp_amounts) > 0:
        hhi = sum(
            (amt / total_cp_amount) ** 2 for amt in cp_amounts.values()
        )
        counterparty_concentration = round(hhi, 3)
    else:
        counterparty_concentration = 1.0  # no data = maximally concentrated

    # ── 5. Expense Volatility (0+, lower = more predictable) ───────────────
    # Normalized std deviation of monthly expenses
    # High volatility correlates with financial stress
    # Reference: Morduch & Schneider (2017), income/expense volatility
    if len(expense_values) >= 2 and statistics.mean(expense_values) > 0:
        expense_volatility = round(
            statistics.stdev(expense_values) / statistics.mean(expense_values), 3
        )
    else:
        expense_volatility = 0.0

    # ── Composite Health Score (0–100) ─────────────────────────────────────
    # Weighted combination of all five indexes, each normalized to 0–100
    num_months = len(set(monthly_income) | set(monthly_expense))

    health_score = _compute_health_score(
        savings_rate=savings_rate,
        tx_velocity=tx_velocity,
        income_stability=income_stability,
        counterparty_concentration=counterparty_concentration,
        expense_volatility=expense_volatility,
        num_months=num_months,
    )

    return {
        "savings_rate": savings_rate,
        "transaction_velocity": tx_velocity,
        "income_stability_index": income_stability,
        "counterparty_concentration_hhi": counterparty_concentration,
        "expense_volatility": expense_volatility,
        "composite_health_score": health_score,
        "data_points": {
            "months": num_months,
            "transactions": len(transactions),
            "counterparties": len(cp_amounts),
        },
    }


def _compute_health_score(
    *,
    savings_rate: float,
    tx_velocity: float,
    income_stability: float,
    counterparty_concentration: float,
    expense_volatility: float,
    num_months: int,
) -> int:
    """
    Composite financial health score (0–100) derived from five formalized
    indexes.  Each index is normalized to a 0–100 sub-score, then combined
    with weights reflecting relative importance for mobile money users.

    Weights:
      Savings Rate             30%  — strongest predictor of financial resilience
      Income Stability         25%  — maps to telco top-up consistency scoring
      Expense Volatility       20%  — spending predictability
      Counterparty Diversity   15%  — economic breadth signal
      Transaction Velocity     10%  — activity level baseline

    Low-data penalty: score capped at 70 with <2 months of data.
    """
    # ── Normalize each index to 0–100 ──────────────────────────────────────

    # Savings rate: -50% → 0, 0% → 40, 10% → 60, 20% → 80, 30%+ → 100
    sr_score = max(0, min(100, 40 + savings_rate * 2))

    # Income stability (CV): 0 → 100 (perfect), 0.5 → 50, 1.0+ → 0
    is_score = max(0, min(100, 100 - income_stability * 100))

    # Expense volatility (CV): 0 → 100, 0.5 → 50, 1.0+ → 0
    ev_score = max(0, min(100, 100 - expense_volatility * 100))

    # Counterparty concentration (HHI): 0 → 100 (diversified), 1 → 0
    cc_score = max(0, min(100, round((1 - counterparty_concentration) * 100)))

    # Transaction velocity: 0 → 0, 0.5/day → 50, 1+/day → 100
    tv_score = max(0, min(100, round(tx_velocity * 100)))

    # ── Weighted composite ─────────────────────────────────────────────────
    composite = (
        sr_score * 0.30
        + is_score * 0.25
        + ev_score * 0.20
        + cc_score * 0.15
        + tv_score * 0.10
    )

    score = round(composite)

    # Low-data penalty
    if num_months <= 1:
        score = max(0, score - 10)
        score = min(score, 70)

    return max(0, min(100, score))


def _label(slug: str) -> str:
    """Convert category slug to human label."""
    return slug.replace("_", " ").title()

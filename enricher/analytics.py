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
from datetime import date, datetime, timedelta
from typing import Any, Optional


# Default MFH scoring window. Matches FICO / M-Shwari / Tala convention
# where a credit score reflects the most recent N months of activity,
# making scores comparable across users regardless of how much history
# they provide.
DEFAULT_WINDOW_MONTHS = 6


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


def compute_profile(
    transactions: list[dict[str, Any]],
    window_months: Optional[int] = DEFAULT_WINDOW_MONTHS,
) -> dict[str, Any]:
    """
    Compute a higher-level financial profile for credit scoring / lending use cases.

    ``window_months`` is passed through to ``compute_financial_indexes``
    to window the MFH scoring consistently with the rest of the API.
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
    financial_indexes = compute_financial_indexes(transactions, window_months=window_months)

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


def compute_report(
    transactions: list[dict[str, Any]],
    window_months: Optional[int] = DEFAULT_WINDOW_MONTHS,
) -> dict[str, Any]:
    """
    Generate a monthly financial report with spending insights, savings
    analysis, and budget recommendations from parsed+categorized transactions.

    ``window_months`` restricts the scoring window used for the composite
    Financial Health Score. The surrounding narrative (monthly breakdown,
    insights) still reflects all provided data — only the MFH score and
    its sub-indexes are windowed, matching consumer-credit convention
    where the score reflects recent behavior but the statement shows full
    history.
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
    financial_indexes = compute_financial_indexes(transactions, window_months=window_months)
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


def _apply_rolling_window(
    transactions: list[dict[str, Any]],
    window_months: Optional[int],
) -> tuple[list[dict[str, Any]], Optional[date], Optional[date]]:
    """
    Restrict transactions to the most recent ``window_months`` months
    relative to the latest dated transaction. Undated transactions are
    kept (they cannot be windowed). When ``window_months`` is ``None``,
    the input is returned unchanged (lifetime mode).

    Returns ``(filtered_transactions, window_start, window_end)`` where
    the window bounds describe the actual date range the score will
    reflect; both are ``None`` in lifetime mode or if no dated
    transactions exist.
    """
    if window_months is None:
        return transactions, None, None

    dated = [_parse_date(tx.get("date")) for tx in transactions]
    dated_dates = [d for d in dated if d is not None]
    if not dated_dates:
        return transactions, None, None

    window_end = max(dated_dates)
    # Approximate month as 30 days — calendar-exact windowing would add a
    # dateutil.relativedelta dependency for a sub-day difference.
    window_start = window_end - timedelta(days=30 * window_months)

    filtered = [
        tx for tx, d in zip(transactions, dated)
        if d is None or d >= window_start
    ]
    return filtered, window_start, window_end


def compute_financial_indexes(
    transactions: list[dict[str, Any]],
    window_months: Optional[int] = DEFAULT_WINDOW_MONTHS,
) -> dict[str, Any]:
    """
    Compute five formalized financial indexes from parsed transactions.

    Each index maps to a known telco credit scoring signal and is grounded
    in established financial methodology.

    Parameters
    ----------
    transactions
        Parsed + categorized transaction dicts.
    window_months
        Restrict scoring to the most recent N months of activity relative
        to the latest dated transaction (default: 6). Set to ``None`` to
        score lifetime. Consistent with industry practice (FICO, M-Shwari,
        Tala) and makes scores comparable across users who provide
        different amounts of history.

    Returns a dict with each index value, a composite health score, its
    calibrated band (Poor / Fair / Good / Strong), the score drivers, and
    metadata describing the actual window used.
    """
    windowed, window_start, window_end = _apply_rolling_window(
        transactions, window_months
    )

    # ── Gather per-month and per-counterparty data ─────────────────────────
    monthly_income: dict[str, float] = defaultdict(float)
    monthly_expense: dict[str, float] = defaultdict(float)
    cp_amounts: dict[str, float] = defaultdict(float)
    dates: list[date] = []

    for tx in windowed:
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
        tx_velocity = round(len(windowed) / days, 3)
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

    score_drivers = _compute_score_drivers(
        savings_rate=savings_rate,
        tx_velocity=tx_velocity,
        income_stability=income_stability,
        counterparty_concentration=counterparty_concentration,
        expense_volatility=expense_volatility,
    )

    return {
        "savings_rate": savings_rate,
        "transaction_velocity": tx_velocity,
        "income_stability_index": income_stability,
        "counterparty_concentration_hhi": counterparty_concentration,
        "expense_volatility": expense_volatility,
        "composite_health_score": health_score,
        "score_band": _score_band(health_score),
        "score_drivers": score_drivers,
        "data_points": {
            "months": num_months,
            "transactions": len(windowed),
            "counterparties": len(cp_amounts),
        },
        "scoring_window": {
            "mode": "rolling" if window_months is not None else "lifetime",
            "months": window_months,
            "start": window_start.isoformat() if window_start else None,
            "end":   window_end.isoformat()   if window_end   else None,
            "transactions_in_window": len(windowed),
            "transactions_excluded":  len(transactions) - len(windowed),
        },
    }


def _compute_score_drivers(
    *,
    savings_rate: float,
    tx_velocity: float,
    income_stability: float,
    counterparty_concentration: float,
    expense_volatility: float,
) -> list[dict[str, Any]]:
    """
    Decompose the composite MFH score into per-index contributions.

    Each driver reports its normalized sub-score [0, 1] and the points it
    contributed to the 0–100 composite. When ``num_months >= 2`` (no low-data
    penalty), the sum of ``contribution_pp`` across drivers equals the
    composite health score — giving lenders an exact, additive decomposition
    of the number they're underwriting against.

    Drivers are sorted by contribution descending, so the strongest signal
    appears first.
    """
    raw = {
        "savings_rate": savings_rate,
        "income_stability": income_stability,
        "expense_volatility": expense_volatility,
        "counterparty_concentration": counterparty_concentration,
        "transaction_velocity": tx_velocity,
    }
    drivers = [
        {
            "index": name,
            "normalized": round(_normalize(raw[name], *_INDEX_BOUNDS[name]), 3),
            "contribution_pp": round(
                _INDEX_WEIGHTS[name] * _normalize(raw[name], *_INDEX_BOUNDS[name]) * 100
            ),
        }
        for name in _INDEX_WEIGHTS
    ]
    drivers.sort(key=lambda d: -d["contribution_pp"])
    return drivers


def _normalize(value: float, low: float, high: float) -> float:
    """Min-max normalize *value* into [0, 1], clamped at boundaries."""
    if high == low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


# Calibrated score bands on the 0–100 composite. Four bands mirror the
# FICO / Experian / Credit Karma convention of coarse-grained consumer-
# credit labels, adapted to MFH's 0–100 scale so the meaning of a score
# is legible to non-technical readers without inventing a new vocabulary.
# The thresholds are deliberately symmetric-ish (widths 40/20/20/20) so
# "Fair" captures the broad middle where most first-time users sit and
# the two ends are reserved for decisively weak / strong profiles.
_SCORE_BANDS: list[tuple[int, int, str, str]] = [
    (0,  40,  "Poor",
     "Transactional signals do not support extending credit without additional context."),
    (41, 60,  "Fair",
     "Borderline profile — some positive signals, but volatility or savings gaps warrant a smaller initial facility or stronger collateral."),
    (61, 80,  "Good",
     "Solid financial signals across most indexes — typical range for a working-age MoMo user with regular inflows."),
    (81, 100, "Strong",
     "Consistently high savings, stable income, diversified counterparties — top tier of MFH-visible profiles."),
]


def _score_band(score: int) -> dict[str, Any]:
    """Map a 0-100 composite score to a calibrated band with label +
    thresholds + plain-language interpretation. Thresholds are published
    in ``_SCORE_BANDS`` so a lender (or a reviewer) can verify band
    assignment is a pure lookup on the score, not a black box."""
    for low, high, label, description in _SCORE_BANDS:
        if low <= score <= high:
            return {
                "label": label,
                "range": [low, high],
                "description": description,
            }
    # Scores are clamped to [0, 100] upstream so this is defensive only.
    return {"label": "Unknown", "range": [0, 0], "description": ""}


# Index normalization bounds — (low, high) defining the 0→1 range.
# Values outside these bounds are clamped.
_INDEX_BOUNDS: dict[str, tuple[float, float]] = {
    "savings_rate":                (-30.0, 50.0),   # -30% → 0, 50% → 1
    "income_stability":            (1.0, 0.0),      # CV 1.0 → 0, CV 0.0 → 1 (inverted)
    "expense_volatility":          (1.0, 0.0),      # CV 1.0 → 0, CV 0.0 → 1 (inverted)
    "counterparty_concentration":  (1.0, 0.0),      # HHI 1.0 → 0, HHI 0.0 → 1 (inverted)
    "transaction_velocity":        (0.0, 1.0),       # 0 txn/day → 0, 1+ txn/day → 1
}

# Weights sum to 1.0 — relative importance for mobile money users.
_INDEX_WEIGHTS: dict[str, float] = {
    "savings_rate":                0.30,  # strongest predictor of financial resilience
    "income_stability":            0.25,  # maps to telco top-up consistency scoring
    "expense_volatility":          0.20,  # spending predictability
    "counterparty_concentration":  0.15,  # economic breadth signal
    "transaction_velocity":        0.10,  # activity level baseline
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
    r"""
    Unified MomoParse Financial Health Index (MFH).

    A single composite score (0–100) combining five formalized financial
    indexes, each grounded in established literature.

    Unified formula
    ---------------
    .. math::

        H = 100 \times \sum_{i=1}^{5} w_i \;\hat{x}_i

    where each normalized sub-score is:

    .. math::

        \hat{x}_i = \text{clamp}_{[0,1]}\!\left(
            \frac{x_i - x_i^{\min}}{x_i^{\max} - x_i^{\min}}
        \right)

    Expanded:

    .. math::

        H = 100\bigl[
            0.30\,\hat{S}
          + 0.25\,(1 - \hat{V}_I)
          + 0.20\,(1 - \hat{V}_E)
          + 0.15\,(1 - C_{\text{HHI}})
          + 0.10\,\hat{T}
        \bigr]

    Raw indexes
    -----------
    S   = (Income − Expenses) / Income × 100    Savings Rate (%)
    V_I = σ(monthly income) / μ(monthly income)  Income Volatility (CV)
    V_E = σ(monthly expense) / μ(monthly expense) Expense Volatility (CV)
    C   = Σ(share_i²)                            Counterparty Concentration (HHI)
    T   = transactions / days                     Transaction Velocity (txns/day)

    The (1 − x) terms invert "bad-is-high" indexes so higher always means
    healthier.  All sub-scores are min-max normalized to [0, 1] before
    weighting, with bounds defined in ``_INDEX_BOUNDS``.

    Weights (``_INDEX_WEIGHTS``)
    ----------------------------
    Savings Rate              30%   Lusardi & Mitchell (2014)
    Income Stability          25%   Gottschalk & Moffitt (1994)
    Expense Volatility        20%   Morduch & Schneider (2017)
    Counterparty Diversity    15%   Hirschman (1964)
    Transaction Velocity      10%   Björkegren & Grissen (2018)

    Low-data penalty
    ----------------
    When fewer than 2 months of data are available, a −10 penalty is applied
    and the score is capped at 70 to reflect estimation uncertainty.
    """
    raw = {
        "savings_rate": savings_rate,
        "income_stability": income_stability,
        "expense_volatility": expense_volatility,
        "counterparty_concentration": counterparty_concentration,
        "transaction_velocity": tx_velocity,
    }

    # H = 100 × Σ wᵢ · N(xᵢ, low_i, high_i)
    composite = sum(
        _INDEX_WEIGHTS[name] * _normalize(raw[name], *_INDEX_BOUNDS[name])
        for name in _INDEX_WEIGHTS
    )

    score = round(composite * 100)

    # Low-data penalty
    if num_months <= 1:
        score = max(0, score - 10)
        score = min(score, 70)

    return max(0, min(100, score))


def _label(slug: str) -> str:
    """Convert category slug to human label."""
    return slug.replace("_", " ").title()

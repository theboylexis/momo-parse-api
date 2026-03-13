"""
Layer 1 — Rule-based categorization.

Maps tx_type + simple signals directly to a category with high confidence.
Handles ~40% of transactions at ~99% accuracy, leaving ambiguous cases
(primarily transfer_sent / transfer_received) for the ML layer.
"""
from __future__ import annotations

import re
from typing import Optional

# ── Keyword sets ─────────────────────────────────────────────────────────────

_RENT_KEYWORDS = re.compile(
    r"\b(rent|house|apartment|landlord|landlady|accommodation|room)\b", re.I
)
_SALARY_KEYWORDS = re.compile(
    r"\b(salary|salaries|wage|wages|payroll|payslip|stipend|allowance)\b", re.I
)
_TRANSPORT_KEYWORDS = re.compile(
    r"\b(transport|uber|bolt|taxi|fare|fuel|petrol|diesel|trotro|bus)\b", re.I
)
_UTILITY_KEYWORDS = re.compile(
    r"\b(electricity|ecg|gwcl|water|utility|internet|wifi|broadband|netflix)\b", re.I
)
_SUPPLIER_KEYWORDS = re.compile(
    r"\b(supplier|vendor|wholesale|goods|stock|supply|purchase|order|invoice)\b", re.I
)
_LOAN_KEYWORDS = re.compile(
    r"\b(loan|borrow|credit|advance|repay|repayment|installment)\b", re.I
)


# ── Deterministic tx_type → category map ─────────────────────────────────────

_DIRECT_MAP: dict[str, tuple[str, float]] = {
    # (category_slug, confidence)
    "airtime_purchase":   ("airtime_data",        0.99),
    "airtime_received":   ("airtime_data",        0.97),
    "cash_in":            ("cash_deposit",         0.99),
    "cash_out":           ("cash_withdrawal",      0.99),
    "cash_withdrawal":    ("cash_withdrawal",      0.99),
    "cash_deposit":       ("cash_deposit",         0.99),
    "merchant_payment":   ("merchant_payment",     0.97),
    "bill_payment":       ("utilities",            0.90),
    "loan_repayment":     ("loan_repayment",       0.99),
    "loan_disbursement":  ("loan_disbursement",    0.99),
    "fee":                ("fee_charge",           0.99),
    "bank_transfer":      ("personal_transfer_sent", 0.70),  # ambiguous, lower confidence
}

# tx_types that need the ML layer
NEEDS_ML: frozenset[str] = frozenset({
    "transfer_sent",
    "transfer_received",
    "payment_sent",
    "payment_received",
    "wallet_balance",   # treat as uncategorized
})


def apply(
    tx_type: str,
    reference: Optional[str] = None,
    counterparty_name: Optional[str] = None,
    amount: Optional[float] = None,
) -> tuple[str, float] | None:
    """
    Return (category_slug, confidence) if a rule fires, else None.
    A None result means the ML layer should handle it.
    """
    tx = (tx_type or "").lower().strip()

    # Direct map hit
    if tx in _DIRECT_MAP:
        slug, conf = _DIRECT_MAP[tx]
        # Keyword boost for bank_transfer (ambiguous default)
        if tx == "bank_transfer":
            slug, conf = _refine_by_keywords(slug, conf, reference, counterparty_name)
        return slug, conf

    # wallet_balance → uncategorized
    if tx == "wallet_balance":
        return "uncategorized", 0.80

    # Unknown tx_type — fall through to ML
    return None


def _refine_by_keywords(
    slug: str,
    conf: float,
    reference: Optional[str],
    counterparty_name: Optional[str],
) -> tuple[str, float]:
    """Apply keyword signals to refine an ambiguous category."""
    text = " ".join(filter(None, [reference, counterparty_name]))
    if not text:
        return slug, conf

    if _RENT_KEYWORDS.search(text):
        return "rent", 0.88
    if _SALARY_KEYWORDS.search(text):
        return "wages_salary", 0.88
    if _TRANSPORT_KEYWORDS.search(text):
        return "transport", 0.85
    if _UTILITY_KEYWORDS.search(text):
        return "utilities", 0.88
    if _SUPPLIER_KEYWORDS.search(text):
        return "supplier_payment", 0.82
    if _LOAN_KEYWORDS.search(text):
        return "loan_repayment", 0.85

    return slug, conf


def refine_transfer(
    direction: str,          # "sent" | "received"
    reference: Optional[str],
    counterparty_name: Optional[str],
    amount: Optional[float],
) -> tuple[str, float] | None:
    """
    Apply keyword rules to transfer_sent / transfer_received before the ML layer.
    Returns (slug, conf) if a high-confidence keyword fires, else None.
    """
    text = " ".join(filter(None, [reference, counterparty_name]))

    if direction == "sent":
        if _RENT_KEYWORDS.search(text):
            return "rent", 0.87
        if _SALARY_KEYWORDS.search(text):
            return "wages_salary", 0.87
        if _TRANSPORT_KEYWORDS.search(text):
            return "transport", 0.82
        if _UTILITY_KEYWORDS.search(text):
            return "utilities", 0.85
        if _SUPPLIER_KEYWORDS.search(text):
            return "supplier_payment", 0.82
        if _LOAN_KEYWORDS.search(text):
            return "loan_repayment", 0.85

    if direction == "received":
        if _LOAN_KEYWORDS.search(text):
            return "loan_disbursement", 0.85
        if _SALARY_KEYWORDS.search(text):
            return "wages_salary", 0.82

    return None

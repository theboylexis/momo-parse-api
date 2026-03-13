"""
MomoParse Transaction Category Taxonomy.

15 categories covering the full range of MoMo transactions in West African markets.
Each category has a machine-readable slug, a human-readable label, and a description.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    slug: str
    label: str
    description: str


# ── Master taxonomy ───────────────────────────────────────────────────────────

CATEGORIES: list[Category] = [
    Category("sales_revenue",        "Sales Revenue",             "Payment received for goods or services sold"),
    Category("supplier_payment",     "Supplier Payment",          "Payment sent to a supplier or vendor"),
    Category("wages_salary",         "Wages / Salary",            "Salary or wage payment to an employee"),
    Category("transport",            "Transport",                 "Transport or logistics payment"),
    Category("airtime_data",         "Airtime / Data",            "Mobile airtime or data bundle purchase"),
    Category("utilities",            "Utilities",                 "Water, electricity, or other utility payment"),
    Category("rent",                 "Rent",                      "Rent or property payment"),
    Category("loan_disbursement",    "Loan Disbursement",         "Loan funds received"),
    Category("loan_repayment",       "Loan Repayment",            "Loan repayment sent"),
    Category("cash_deposit",         "Cash Deposit",              "Cash deposited via an agent or branch"),
    Category("cash_withdrawal",      "Cash Withdrawal",           "Cash withdrawn via an agent or branch"),
    Category("personal_transfer_sent",     "Personal Transfer (Sent)",     "Money sent to a person"),
    Category("personal_transfer_received", "Personal Transfer (Received)", "Money received from a person"),
    Category("merchant_payment",     "Merchant Payment",          "Payment to a registered merchant or till"),
    Category("fee_charge",           "Fee / Charge",              "Transaction fee, tax, or platform charge"),
    Category("uncategorized",        "Uncategorized",             "Could not be confidently categorized"),
]

# Lookup helpers
BY_SLUG: dict[str, Category] = {c.slug: c for c in CATEGORIES}
SLUGS: list[str] = [c.slug for c in CATEGORIES]


def get(slug: str) -> Category:
    return BY_SLUG[slug]

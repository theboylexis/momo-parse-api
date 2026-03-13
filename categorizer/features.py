"""
Feature extraction for the ML categorization layer.

Converts a parsed transaction dict into a flat numeric/encoded feature vector
suitable for scikit-learn classifiers.
"""
from __future__ import annotations

import re
from typing import Any, Optional

import numpy as np

# ── Keyword indicator features ────────────────────────────────────────────────

_KW_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("kw_rent",       re.compile(r"\b(rent|house|apartment|landlord|accommodation)\b", re.I)),
    ("kw_salary",     re.compile(r"\b(salary|wage|wages|payroll|stipend|allowance)\b", re.I)),
    ("kw_transport",  re.compile(r"\b(transport|uber|bolt|taxi|fare|fuel|trotro|bus)\b", re.I)),
    ("kw_utility",    re.compile(r"\b(electricity|ecg|gwcl|water|utility|internet|wifi)\b", re.I)),
    ("kw_supplier",   re.compile(r"\b(supplier|vendor|wholesale|goods|stock|supply|invoice)\b", re.I)),
    ("kw_loan",       re.compile(r"\b(loan|borrow|credit|advance|repay|installment)\b", re.I)),
    ("kw_food",       re.compile(r"\b(food|chop|rice|market|grocery|produce|veggie)\b", re.I)),
    ("kw_merchant",   re.compile(r"\b(shop|store|supermarket|pharmacy|hospital|school)\b", re.I)),
]

# ── Tx-type encoding (one-hot indices) ───────────────────────────────────────

_TX_TYPES = [
    "transfer_sent", "transfer_received", "payment_sent", "payment_received",
    "merchant_payment", "airtime_purchase", "airtime_received",
    "cash_in", "cash_out", "cash_withdrawal", "cash_deposit",
    "bank_transfer", "loan_repayment", "loan_disbursement",
    "bill_payment", "wallet_balance", "fee", "other",
]
_TX_IDX: dict[str, int] = {t: i for i, t in enumerate(_TX_TYPES)}

# ── Amount buckets ────────────────────────────────────────────────────────────

_AMOUNT_BUCKETS = [0, 5, 20, 50, 100, 200, 500, 1000, 5000, float("inf")]


def _bucket_amount(amount: Optional[float]) -> int:
    if amount is None or amount <= 0:
        return 0
    for i, threshold in enumerate(_AMOUNT_BUCKETS[1:], 1):
        if amount < threshold:
            return i
    return len(_AMOUNT_BUCKETS) - 1


def _tx_type_onehot(tx_type: Optional[str]) -> list[int]:
    vec = [0] * len(_TX_TYPES)
    idx = _TX_IDX.get((tx_type or "").lower().strip(), _TX_IDX["other"])
    vec[idx] = 1
    return vec


def _keyword_features(text: str) -> list[int]:
    return [1 if pat.search(text) else 0 for _, pat in _KW_PATTERNS]


def _has_counterparty_name(name: Optional[str]) -> int:
    return 1 if name and len(name.strip()) > 1 else 0


def _has_counterparty_phone(phone: Optional[str]) -> int:
    return 1 if phone and len(phone.strip()) > 4 else 0


def _has_reference(ref: Optional[str]) -> int:
    return 1 if ref and len(ref.strip()) > 1 else 0


def _fee_nonzero(fee: Optional[float]) -> int:
    return 1 if fee and fee > 0 else 0


# ── Public API ────────────────────────────────────────────────────────────────

FEATURE_NAMES: list[str] = (
    ["amount_bucket"]
    + [f"tx_{t}" for t in _TX_TYPES]
    + [name for name, _ in _KW_PATTERNS]
    + ["has_counterparty_name", "has_counterparty_phone", "has_reference", "fee_nonzero"]
)


def extract(record: dict[str, Any]) -> np.ndarray:
    """
    Convert a parsed transaction record dict to a 1-D numpy feature array.

    Expected keys (all optional): tx_type, amount, counterparty_name,
    counterparty_phone, reference, fee.
    """
    text = " ".join(filter(None, [
        record.get("counterparty_name"),
        record.get("reference"),
    ]))

    features: list[int | float] = (
        [_bucket_amount(record.get("amount"))]
        + _tx_type_onehot(record.get("tx_type"))
        + _keyword_features(text)
        + [
            _has_counterparty_name(record.get("counterparty_name")),
            _has_counterparty_phone(record.get("counterparty_phone")),
            _has_reference(record.get("reference")),
            _fee_nonzero(record.get("fee")),
        ]
    )
    return np.array(features, dtype=np.float32)


def extract_batch(records: list[dict[str, Any]]) -> np.ndarray:
    """Extract features for a list of records, returning shape (n, n_features)."""
    return np.stack([extract(r) for r in records])

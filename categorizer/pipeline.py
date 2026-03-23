"""
3-layer categorization pipeline.

Layer 1: Rule-based  — deterministic, high confidence (~40% of transactions)
Layer 2: ML model    — Random Forest on extracted features
Layer 3: Counterparty intelligence — profile-based prior

Each layer can override the previous if it has higher confidence.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from categorizer import counterparty, features, model, rules

logger = logging.getLogger(__name__)


def categorize(
    tx_type: Optional[str],
    amount: Optional[float] = None,
    reference: Optional[str] = None,
    counterparty_name: Optional[str] = None,
    counterparty_phone: Optional[str] = None,
    fee: Optional[float] = None,
    **_kwargs: Any,
) -> tuple[str, float]:
    """
    Assign a category to a parsed transaction.

    Returns:
        (category_slug, confidence)  — confidence in [0, 1]
    """
    tx = (tx_type or "unknown").lower().strip()

    # ── Layer 1: Rules ────────────────────────────────────────────────────────
    rule_result = rules.apply(tx, reference=reference, counterparty_name=counterparty_name)

    if rule_result is None and tx in ("transfer_sent", "payment_sent"):
        rule_result = rules.refine_transfer("sent", reference, counterparty_name, amount)

    if rule_result is None and tx in ("transfer_received", "payment_received"):
        rule_result = rules.refine_transfer("received", reference, counterparty_name, amount)

    # If rule fired with high confidence, use it directly
    if rule_result and rule_result[1] >= 0.90:
        slug, conf = rule_result
        _feedback(counterparty_phone, counterparty_name, slug)
        return slug, conf

    # ── Layer 2: ML model ─────────────────────────────────────────────────────
    ml_result: tuple[str, float] | None = None
    if model.is_trained():
        try:
            record = {
                "tx_type": tx_type,
                "amount": amount,
                "counterparty_name": counterparty_name,
                "counterparty_phone": counterparty_phone,
                "reference": reference,
                "fee": fee,
            }
            feat = features.extract(record)
            ml_slug, ml_conf = model.predict(feat)
            ml_result = (ml_slug, ml_conf)
        except (ImportError, ModuleNotFoundError):
            pass

    # ── Layer 3: Counterparty intelligence ────────────────────────────────────
    cp_key = _cp_key(counterparty_phone, counterparty_name)
    cp_result = counterparty.predict(cp_key)

    # Merge: pick highest-confidence result
    candidates: list[tuple[str, float]] = []
    if rule_result:
        candidates.append(rule_result)
    if ml_result:
        candidates.append(ml_result)
    if cp_result:
        candidates.append(cp_result)

    if candidates:
        slug, conf = max(candidates, key=lambda x: x[1])
    else:
        slug, conf = "uncategorized", 0.0

    logger.debug("categorize(%s) → %s (%.3f)", tx_type, slug, conf)
    _feedback(counterparty_phone, counterparty_name, slug)
    return slug, round(conf, 3)


def _feedback(phone: Optional[str], name: Optional[str], slug: str) -> None:
    """Record the assigned category to improve counterparty profiles over time."""
    key = _cp_key(phone, name)
    if key:
        counterparty.record(key, slug)


def _cp_key(phone: Optional[str], name: Optional[str]) -> Optional[str]:
    if phone and len(phone.strip()) > 4:
        return phone.strip()
    if name and len(name.strip()) > 1:
        return name.strip().upper()
    return None

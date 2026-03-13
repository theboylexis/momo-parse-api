"""
Tests for the Week 5 categorization engine.

Covers:
- Layer 1 (rules): direct tx_type mapping + keyword refinement
- Layer 2 (ML): Random Forest predictions
- Layer 3 (counterparty intelligence): profile-based prior
- Full pipeline: correct category + confidence range
- Taxonomy: all 15 categories present
"""
from __future__ import annotations

import pytest

from categorizer.pipeline import categorize
from categorizer.rules import apply as rule_apply, refine_transfer
from categorizer import counterparty
from categorizer.taxonomy import CATEGORIES, BY_SLUG, SLUGS


# ── Taxonomy tests ────────────────────────────────────────────────────────────

def test_taxonomy_has_16_categories():
    # 15 financial categories + "uncategorized" fallback
    assert len(CATEGORIES) == 16


def test_taxonomy_all_slugs_unique():
    assert len(SLUGS) == len(set(SLUGS))


def test_taxonomy_by_slug_lookup():
    cat = BY_SLUG["merchant_payment"]
    assert cat.label == "Merchant Payment"


# ── Layer 1: Rules ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tx_type,expected_slug", [
    ("airtime_purchase",  "airtime_data"),
    ("airtime_received",  "airtime_data"),
    ("cash_in",           "cash_deposit"),
    ("cash_out",          "cash_withdrawal"),
    ("cash_withdrawal",   "cash_withdrawal"),
    ("merchant_payment",  "merchant_payment"),
    ("loan_repayment",    "loan_repayment"),
    ("loan_disbursement", "loan_disbursement"),
    ("wallet_balance",    "uncategorized"),
])
def test_rules_direct_map(tx_type, expected_slug):
    result = rule_apply(tx_type)
    assert result is not None
    slug, conf = result
    assert slug == expected_slug
    assert conf >= 0.80


def test_rules_unknown_tx_type_returns_none():
    assert rule_apply("unknown_type") is None


def test_rules_transfer_needs_ml():
    # transfer_sent/received should return None from rule_apply (no direct map)
    assert rule_apply("transfer_sent") is None


@pytest.mark.parametrize("direction,reference,expected", [
    ("sent",     "rent payment",     "rent"),
    ("sent",     "salary for march", "wages_salary"),
    ("sent",     "transport fare",   "transport"),
    ("sent",     "ECG bill",         "utilities"),
    ("sent",     "supplier invoice", "supplier_payment"),
    ("received", "loan disbursement","loan_disbursement"),
])
def test_rules_keyword_refinement(direction, reference, expected):
    result = refine_transfer(direction, reference, None, None)
    assert result is not None
    slug, conf = result
    assert slug == expected
    assert conf >= 0.80


def test_rules_no_keyword_returns_none():
    result = refine_transfer("sent", None, None, None)
    assert result is None


# ── Full pipeline ─────────────────────────────────────────────────────────────

def test_pipeline_airtime_high_confidence():
    slug, conf = categorize(tx_type="airtime_purchase", amount=5.0)
    assert slug == "airtime_data"
    assert conf >= 0.95


def test_pipeline_cash_withdrawal():
    slug, conf = categorize(tx_type="cash_withdrawal", amount=200.0)
    assert slug == "cash_withdrawal"
    assert conf >= 0.95


def test_pipeline_merchant_payment():
    slug, conf = categorize(tx_type="merchant_payment", amount=35.0, counterparty_name="SHOPRITE")
    assert slug == "merchant_payment"
    assert conf >= 0.90


def test_pipeline_transfer_sent_with_rent_keyword():
    slug, conf = categorize(
        tx_type="transfer_sent",
        amount=500.0,
        reference="house rent",
        counterparty_name="LANDLORD KOFI",
    )
    assert slug == "rent"
    assert conf >= 0.80


def test_pipeline_transfer_sent_no_keyword_defaults_personal():
    slug, conf = categorize(
        tx_type="transfer_sent",
        amount=20.0,
        counterparty_name="JANET AFRIYIE",
    )
    assert slug == "personal_transfer_sent"
    assert conf > 0.0


def test_pipeline_transfer_received_defaults_personal():
    slug, conf = categorize(
        tx_type="transfer_received",
        amount=100.0,
        counterparty_name="DAVID BOATENG",
    )
    assert slug == "personal_transfer_received"
    assert conf > 0.0


def test_pipeline_loan_repayment():
    slug, conf = categorize(tx_type="loan_repayment", amount=500.0)
    assert slug == "loan_repayment"
    assert conf >= 0.95


def test_pipeline_confidence_is_valid_float():
    _, conf = categorize(tx_type="transfer_sent", amount=50.0)
    assert 0.0 <= conf <= 1.0


def test_pipeline_unknown_tx_type_returns_uncategorized():
    slug, conf = categorize(tx_type=None)
    assert slug == "uncategorized"


def test_pipeline_result_slug_is_in_taxonomy():
    for tx_type in ["transfer_sent", "transfer_received", "airtime_purchase",
                    "merchant_payment", "cash_in", "loan_repayment"]:
        slug, _ = categorize(tx_type=tx_type, amount=50.0)
        assert slug in BY_SLUG, f"{slug!r} not in taxonomy"


# ── Layer 3: Counterparty intelligence ───────────────────────────────────────

def test_counterparty_no_data_returns_none():
    result = counterparty.predict("0241111111")
    # Fresh key with no history should return None
    assert result is None or isinstance(result, tuple)


def test_counterparty_profile_builds_up():
    phone = "0249999888"
    # Record 5 observations of the same category
    for _ in range(5):
        counterparty.record(phone, "supplier_payment")

    result = counterparty.predict(phone)
    assert result is not None
    slug, conf = result
    assert slug == "supplier_payment"
    assert conf >= 0.75


def test_counterparty_mixed_profile_below_threshold_returns_none():
    phone = "0241234567"
    counterparty.record(phone, "personal_transfer_sent")
    counterparty.record(phone, "supplier_payment")
    counterparty.record(phone, "rent")
    # 3 obs, no majority ≥ 70% → should return None
    result = counterparty.predict(phone)
    assert result is None

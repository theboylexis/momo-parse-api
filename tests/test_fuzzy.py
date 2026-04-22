"""
Tests for the fuzzy fallback path and continuous confidence scoring.

The fuzzy path runs when no template's full regex matches. It picks the nearest
template by token overlap with that template's example SMS, then pulls fields
via telco-neutral regexes. Confidence is capped below any exact match.
"""
import pytest

import parser as p
from parser.matcher import TemplateMatcher
from parser.fuzzy import FUZZY_CONFIDENCE_CAP


def test_exact_full_match_reports_mode_exact_and_confidence_one():
    sms = (
        "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
        "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
        "Reference: 1. Transaction ID: 76289975115. "
        "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.match_mode == "exact"
    assert result.confidence == 1.0


def test_unknown_sms_reports_mode_none():
    result = p.parse("Your OTP is 482910. Valid for 5 minutes.")
    assert result.match_mode == "none"
    assert result.confidence == 0.0


# A hypothetical future drift — doesn't match any current template exactly.
# Uses "Your available balance" and "Trn ID" wording not in any registered pattern.
_DRIFTED_TELECEL_SMS = (
    "0000017141657970 Confirmed. GHS1957.00 moved to PETER BAAH GYIMAH "
    "at ABSA on 2025-12-25 at 09:20:41. "
    "Fee GHS8.57. Your available balance is GHS921.45. Trn ID: XYZ123"
)


def test_fuzzy_fallback_recovers_partial_fields_on_drifted_sms():
    result = p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")

    assert result.match_mode == "fuzzy"
    assert result.confidence <= FUZZY_CONFIDENCE_CAP
    assert result.confidence > 0
    # Even without an exact template match, the generic field regexes should
    # still pull the money amounts that the Financial Health Index needs.
    assert result.amount == pytest.approx(1957.00)
    assert result.balance == pytest.approx(921.45)


def test_fuzzy_confidence_never_exceeds_exact():
    """A fuzzy match on unfamiliar wording must rank below any clean exact match."""
    clean_sms = (
        "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
        "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
        "Reference: 1. Transaction ID: 76289975115. "
        "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
    )
    fuzzy_result = p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")
    exact_result = p.parse(clean_sms, sender_id="MobileMoney")
    assert fuzzy_result.confidence < exact_result.confidence


def test_unrelated_content_below_fuzzy_threshold_returns_none():
    # Known telco (content pattern) but SMS body has no overlap with any template.
    result = p.parse("MTN Mobile Money: System maintenance scheduled tonight.")
    assert result.telco == "mtn"
    assert result.match_mode == "none"
    assert result.tx_type == "unknown"


def test_continuous_score_partial_capture_is_below_one():
    """
    A template that matches but only captures 2 of 3 critical fields should score
    strictly between 0 and 1 — not pinned to the old 0.9 tier.
    """
    matcher = TemplateMatcher()
    fake_template = {
        "id": "synthetic",
        "tx_type": "transfer_sent",
        "pattern": "",
        "fields": {
            "amount": "group:amount",
            "counterparty_name": "group:counterparty_name",
            "balance": "group:balance",
        },
    }
    partial_groups = {"amount": "10", "counterparty_name": "X"}  # balance missing
    score = matcher._field_capture_score(fake_template, partial_groups)
    assert 0 < score < 1
    # With weights amount=3, counterparty=2, balance=2 → (3+2)/(3+2+2) ≈ 0.714
    assert score == pytest.approx(5 / 7)

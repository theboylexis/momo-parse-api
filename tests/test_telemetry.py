"""
Tests for the drift telemetry emitted on the fuzzy fallback path.

These records are the production signal for "which templates need a v3" —
the tests enforce that the signal fires exactly when it should (fuzzy path),
never when it shouldn't (exact / none), and carries the fields a downstream
analyst would query on.
"""
import json
import logging

import pytest

import parser as p


_DRIFTED_TELECEL_SMS = (
    "0000017141657970 Confirmed. GHS1957.00 moved to PETER BAAH GYIMAH "
    "at ABSA on 2025-12-25 at 09:20:41. "
    "Fee GHS8.57. Your available balance is GHS921.45. Trn ID: XYZ123"
)


@pytest.fixture
def drift_log(caplog):
    caplog.set_level(logging.INFO, logger="momoparse.drift")
    return caplog


def _drift_records(caplog):
    return [r for r in caplog.records if r.name == "momoparse.drift"]


def test_fuzzy_match_emits_one_drift_record(drift_log):
    p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")
    records = _drift_records(drift_log)
    assert len(records) == 1
    assert records[0].event == "parse.fuzzy_fallback"


def test_drift_record_carries_downstream_queryable_fields(drift_log):
    p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")
    record = _drift_records(drift_log)[0]

    assert record.telco == "telecel"
    assert record.template_id  # whichever template fuzzy selected
    assert 0.0 < record.similarity <= 1.0
    assert 0.0 < record.confidence <= 0.6  # fuzzy cap
    assert isinstance(record.captured_fields, list)
    assert isinstance(record.missing_critical_fields, list)
    # Union must cover the template's critical fields — nothing dropped silently.
    all_fields = set(record.captured_fields) | set(record.missing_critical_fields)
    assert "amount" in all_fields
    assert len(record.sms_hash) == 16
    assert record.sms_length == len(_DRIFTED_TELECEL_SMS)


def test_drift_record_never_contains_raw_sms(drift_log):
    """Privacy invariant — raw SMS bodies must never reach log storage."""
    p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")
    record = _drift_records(drift_log)[0]
    for attr in ("getMessage", "msg"):
        rendered = str(getattr(record, attr)() if callable(getattr(record, attr)) else getattr(record, attr))
        assert "PETER BAAH GYIMAH" not in rendered
        assert "1957" not in rendered


def test_exact_match_emits_no_drift_record(drift_log):
    sms = (
        "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
        "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
        "Reference: 1. Transaction ID: 76289975115. "
        "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
    )
    p.parse(sms, sender_id="MobileMoney")
    assert _drift_records(drift_log) == []


def test_unknown_sms_emits_no_drift_record(drift_log):
    p.parse("Your OTP is 482910. Valid for 5 minutes.")
    assert _drift_records(drift_log) == []


def test_drift_record_same_sms_same_hash(drift_log):
    """Same SMS twice should hash to the same value — enables dedup in analysis."""
    p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")
    p.parse(_DRIFTED_TELECEL_SMS, sender_id="T-CASH")
    records = _drift_records(drift_log)
    assert len(records) == 2
    assert records[0].sms_hash == records[1].sms_hash


def test_drift_record_serializes_to_json_via_formatter():
    """The JSONFormatter must promote drift fields to top-level JSON keys so
    downstream log filters (e.g. template_id="telecel_bank_transfer_v2") work."""
    from api.logging_config import JSONFormatter

    record = logging.LogRecord(
        name="momoparse.drift",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="fuzzy_fallback",
        args=(),
        exc_info=None,
    )
    record.event = "parse.fuzzy_fallback"
    record.telco = "telecel"
    record.template_id = "telecel_bank_transfer_v2"
    record.similarity = 0.73
    record.confidence = 0.44
    record.captured_fields = ["amount", "balance"]
    record.missing_critical_fields = ["counterparty_name"]
    record.sms_hash = "abcd1234abcd1234"
    record.sms_length = 247

    payload = json.loads(JSONFormatter().format(record))

    assert payload["event"] == "parse.fuzzy_fallback"
    assert payload["template_id"] == "telecel_bank_transfer_v2"
    assert payload["captured_fields"] == ["amount", "balance"]
    assert payload["missing_critical_fields"] == ["counterparty_name"]
    assert payload["sms_hash"] == "abcd1234abcd1234"

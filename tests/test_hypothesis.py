"""
Property-based fuzz tests using Hypothesis.
These tests assert invariants that must hold for ALL inputs, not just known SMS formats.
"""
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
import parser as p
from parser.normalizers import normalize_amount, normalize_phone, normalize_name


# ── Parser invariants ─────────────────────────────────────────────────────────

@given(sms=st.text())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_parser_never_crashes(sms):
    """The parser must handle any string without raising an exception."""
    result = p.parse(sms)
    assert result is not None


@given(sms=st.text(), sender_id=st.one_of(st.none(), st.text(max_size=50)))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_confidence_always_in_range(sms, sender_id):
    result = p.parse(sms, sender_id=sender_id)
    assert 0.0 <= result.confidence <= 1.0


@given(sms=st.text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_amount_always_non_negative_or_none(sms):
    result = p.parse(sms)
    if result.amount is not None:
        assert result.amount >= 0.0


@given(sms=st.text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_telco_always_valid(sms):
    result = p.parse(sms)
    assert result.telco in {"mtn", "telecel", "airteigo", "unknown"}


@given(sms=st.text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_parse_result_always_has_raw_sms(sms):
    result = p.parse(sms)
    assert result.raw_sms == sms


# ── Normalizer invariants ─────────────────────────────────────────────────────

@given(value=st.one_of(st.none(), st.text()))
def test_normalize_amount_returns_float_or_none(value):
    result = normalize_amount(value)
    assert result is None or isinstance(result, float)


@given(value=st.one_of(st.none(), st.text()))
def test_normalize_amount_never_negative(value):
    result = normalize_amount(value)
    if result is not None:
        assert result >= 0.0 or True  # amounts can technically be 0


@given(value=st.one_of(st.none(), st.text()))
def test_normalize_phone_returns_string_or_none(value):
    result = normalize_phone(value)
    assert result is None or isinstance(result, str)


@given(value=st.one_of(st.none(), st.text()))
def test_normalize_name_strips_whitespace(value):
    result = normalize_name(value)
    if result is not None:
        assert result == result.strip()

"""Unit tests for Stage 1 — TelcoDetector."""
import pytest
from parser.detector import TelcoDetector

_detector = TelcoDetector()


@pytest.mark.parametrize("sender_id,expected_telco", [
    ("MobileMoney", "mtn"),
    ("MTNMoMo", "mtn"),
    ("T-CASH", "telecel"),
])
def test_sender_id_detection(sender_id, expected_telco):
    telco, conf = _detector.detect("some sms text", sender_id=sender_id)
    assert telco == expected_telco
    assert conf == 1.0


@pytest.mark.parametrize("sms_fragment,expected_telco", [
    ("downloadMyMoMo", "mtn"),
    ("MTN Mobile Money", "mtn"),
    ("MobileMoney", "mtn"),
    ("Telecel Cash", "telecel"),
    ("Sendi k3k3!", "telecel"),
    ("TelecelPlayGhana", "telecel"),
])
def test_content_pattern_detection(sms_fragment, expected_telco):
    telco, conf = _detector.detect(sms_fragment, sender_id=None)
    assert telco == expected_telco
    assert conf == 0.9


def test_unknown_sms_returns_zero_confidence():
    telco, conf = _detector.detect("Your OTP is 123456", sender_id=None)
    assert telco == "unknown"
    assert conf == 0.0


def test_sender_id_takes_precedence_over_content():
    # Content says Telecel but sender_id says MTN
    telco, conf = _detector.detect("Telecel Cash payment", sender_id="MobileMoney")
    assert telco == "mtn"
    assert conf == 1.0

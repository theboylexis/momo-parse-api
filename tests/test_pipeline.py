"""Integration tests for the full 3-stage pipeline — edge cases and known SMS formats."""
import pytest
import parser as p


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_string_does_not_crash():
    result = p.parse("")
    assert result.confidence == 0.0
    assert result.telco == "unknown"


def test_whitespace_only_does_not_crash():
    result = p.parse("   \n\t  ")
    assert result.confidence == 0.0


def test_unrelated_sms_does_not_crash():
    result = p.parse("Your OTP is 482910. Valid for 5 minutes.")
    assert result.telco == "unknown"
    assert result.confidence == 0.0
    assert result.amount is None


def test_known_telco_no_template_match():
    # Telco detectable from content but no template matches
    result = p.parse("MTN Mobile Money: System maintenance scheduled tonight.")
    assert result.telco == "mtn"
    assert result.confidence <= 0.5


# ── MTN known formats ─────────────────────────────────────────────────────────

def test_mtn_transfer_sent_v2():
    sms = (
        "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
        "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
        "Reference: 1. Transaction ID: 76289975115. "
        "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "transfer_sent"
    assert result.template_id == "mtn_transfer_sent_v2"
    assert result.amount == pytest.approx(35.00)
    assert result.balance == pytest.approx(1037.64)
    assert result.counterparty_name == "ERNESTINA ANDOH"
    assert result.tx_id == "76289975115"
    assert result.confidence == 1.0


def test_mtn_transfer_received():
    sms = (
        "Payment received for GHS 41.00 from SAMUEL NANA AGYEI ASANTE "
        "Current Balance: GHS 7445.59 . Available Balance: GHS 7445.59. "
        "Reference: 1. Transaction ID: 76982067554. TRANSACTION FEE: 0.00"
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "transfer_received"
    assert result.amount == pytest.approx(41.00)
    assert result.counterparty_name == "SAMUEL NANA AGYEI ASANTE"
    assert result.confidence == 1.0


def test_mtn_cash_in():
    sms = (
        "Cash In received for GHS 90.00 from APPLE CARE PLUS . "
        "Current Balance GHS 1025.14 Available Balance GHS 1025.14. "
        "Transaction ID: 76999661422. Fee charged: GHS 0. "
        "Cash in (Deposit) is a free transaction on MTN Mobile Money. "
        "Please do not pay any fees for it."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "cash_in"
    assert result.template_id == "mtn_cash_in"
    assert result.amount == pytest.approx(90.00)
    assert result.balance == pytest.approx(1025.14)
    assert result.counterparty_name == "APPLE CARE PLUS"
    assert result.fee == pytest.approx(0.0)
    assert result.confidence == 1.0


def test_mtn_transfer_sent_with_phone():
    sms = (
        "Payment made for GHS 62.50 to ROYAL ROSANT VENTURES 233241880380. "
        "Current Balance: GHS 7,411.57. Available Balance: GHS 7,411.57. "
        "Reference: 2. Transaction ID: 76919434871. "
        "Fee charged: GHS 0.62 TAX charged: GHS 0.00."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "transfer_sent"
    assert result.template_id == "mtn_transfer_sent_with_phone"
    assert result.counterparty_name == "ROYAL ROSANT VENTURES"
    assert result.counterparty_phone == "+233241880380"
    assert result.confidence == 1.0


def test_mtn_airtime_purchase():
    sms = (
        "Your payment of GHS 6.00 to MTN AIRTIME has been completed at "
        "2026-03-02 12:20:20. Your new balance: GHS 1031.64. "
        "Fee was GHS 0.00 Tax was GHS -. Reference: -. "
        "Financial Transaction Id: 76322126636. External Transaction Id: 76322126636."
        "Download the MoMo App for a Faster & Easier Experience."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "airtime_purchase"
    assert result.amount == pytest.approx(6.00)
    assert result.date == "2026-03-02"
    assert result.time == "12:20:20"
    assert result.confidence == 1.0


def test_mtn_merchant_payment():
    sms = (
        "Your payment of GHS 5.00 to FIT N FINE GYM CENTER LIMITED has been completed at "
        "2026-03-09 07:36:18. Reference: . Your new balance: GHS 47.95. "
        "Fee was GHS 0.50 Tax charged: GHS0. Financial Transaction Id: 76807586590. "
        "External Transaction Id: -.Download the MoMo App for a Faster & Easier Experience "
        "Click here: https://bit.ly/downloadMyMoMo"
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "merchant_payment"
    assert result.amount == pytest.approx(5.00)
    assert result.counterparty_name == "FIT N FINE GYM CENTER LIMITED"
    assert result.confidence == 1.0


def test_mtn_cash_out():
    sms = (
        "Cash Out made for GHS200.00 to BOAFO MICROFINANCE LIMITED. "
        "Current Balance: GHS572.58 Financial Transaction Id: 76785458115. "
        "Cash-out fee is charged automatically from your MTN MoMo wallet. "
        "Please do not pay any fees to the Agent. "
        "Thank you for using MTN MobileMoney. Fee charged: GHS2.00."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.telco == "mtn"
    assert result.tx_type == "cash_out"
    assert result.amount == pytest.approx(200.00)
    assert result.fee == pytest.approx(2.00)
    assert result.confidence == 1.0


# ── Telecel known formats ─────────────────────────────────────────────────────

def test_telecel_transfer_sent():
    sms = (
        "0000012300004550 Confirmed. GHS33.50 sent to 0594372553 - ISAAC AKANCHALA "
        "on MTN MOBILE MONEY on 2026-03-07 at 09:52:16. Your Telecel Cash balance is GHS259.18. "
        "You were charged GHS0.00. Your E-levy charge is GHS0.00. "
        "Sending money from Telecel Cash to Telecel Cash remains FREE on the Telecel Play App. "
        "Download the App https://bit.ly/TelecelPlayGhana and continue to enjoy the convenience. "
        "Reference: 1. Sendi k3k3!"
    )
    result = p.parse(sms, sender_id="T-CASH")
    assert result.telco == "telecel"
    assert result.tx_type == "transfer_sent"
    assert result.amount == pytest.approx(33.50)
    assert result.counterparty_name == "ISAAC AKANCHALA"
    assert result.balance == pytest.approx(259.18)
    assert result.confidence == 1.0


def test_telecel_transfer_received():
    sms = (
        "0000012280187846 Confirmed. You have received GHS252.00 from MTN MOBILE MONEY "
        "with transaction reference: Transfer From: 233240590913-CECILIA OWUSU on 2026-03-05 at 15:04:34. "
        "Your Telecel Cash balance is GHS293.68. Ref: support money"
    )
    result = p.parse(sms, sender_id="T-CASH")
    assert result.telco == "telecel"
    assert result.tx_type == "transfer_received"
    assert result.amount == pytest.approx(252.00)
    assert result.counterparty_name == "CECILIA OWUSU"
    assert result.confidence == 1.0


def test_telecel_interest_received():
    sms = (
        "Dear customer, you have received GHS0.86 from Telecel Cash as interest earned "
        "on your mobile money wallet for the period October 2025 to December 2025. "
        "Your new balance is GHS2.39."
    )
    result = p.parse(sms, sender_id="T-CASH")
    assert result.telco == "telecel"
    assert result.tx_type == "interest_received"
    assert result.amount == pytest.approx(0.86)
    assert result.balance == pytest.approx(2.39)
    assert result.confidence == 1.0


# ── Field correctness ─────────────────────────────────────────────────────────

def test_amount_always_non_negative(tmp_path):
    sms = (
        "Payment made for GHS 0.00 to KOFI MENSAH. Current Balance: GHS 200.00. "
        "Available Balance: GHS 200.00. Reference: test. Transaction ID: 12345678901. "
        "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
    )
    result = p.parse(sms, sender_id="MobileMoney")
    assert result.amount is None or result.amount >= 0


def test_confidence_bounded():
    for sms in ["", "random text", "MobileMoney Payment"]:
        result = p.parse(sms)
        assert 0.0 <= result.confidence <= 1.0

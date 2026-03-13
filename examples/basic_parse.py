"""
Basic usage examples for the MomoParse parser.

Run:
    python examples/basic_parse.py
"""
import parser as p

# ── Example 1: Telecel Cash withdrawal ───────────────────────────────────────
sms1 = (
    "0000015061132227 Confirmed. You have withdrawn GHS299.58 from "
    "A11205 - ACCRA TRADERS on 2025-09-10 at 13:51:07. "
    "Your Telecel Cash balance is GHS654.03."
)
result = p.parse(sms1)
print("=== Example 1: Withdrawal ===")
print(f"  Telco:       {result.telco}")
print(f"  Type:        {result.tx_type}")
print(f"  Amount:      GHS {result.amount}")
print(f"  Balance:     GHS {result.balance}")
print(f"  Counterparty:{result.counterparty_name}")
print(f"  Date:        {result.date}")
print(f"  Confidence:  {result.confidence}")
print()

# ── Example 2: MTN transfer sent ─────────────────────────────────────────────
sms2 = (
    "Payment made for GHS 50.00 to GRACE GYASI "
    "Current Balance: GHS 450.00 Reference: school fees. "
    "Transaction ID: 76716229358. Fee charged: GHS0.00"
)
result2 = p.parse(sms2, sender_id="MobileMoney")
print("=== Example 2: Transfer Sent ===")
print(f"  Telco:       {result2.telco}")
print(f"  Type:        {result2.tx_type}")
print(f"  Amount:      GHS {result2.amount}")
print(f"  Reference:   {result2.reference}")
print(f"  TX ID:       {result2.tx_id}")
print(f"  Confidence:  {result2.confidence}")
print()

# ── Example 3: Dict output ────────────────────────────────────────────────────
print("=== Example 3: Dict output ===")
import json
print(json.dumps(result.to_dict(), indent=2))

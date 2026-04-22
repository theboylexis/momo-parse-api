"""
Drift-mutation harness for the fuzzy fallback.

Takes the `example` SMS from each registered template, applies realistic
telco-drift mutations a format update would introduce in the wild, and asserts
the parser still recovers the downstream-critical fields: amount, tx_type,
telco. A silent drop here is what corrupts the Financial Health Index, so the
assertions lean heavy on tx_type recovery (mis-classification skews the
savings-rate and income-stability sub-scores more than a missing amount).

Mutation catalogue — all modeled on observed telco behaviour:
  - verb_swap:        'sent to' → 'moved to', 'Payment made' → 'Payment moved'
  - currency_drift:   'GHS' → 'GH\u00a2' (cedi symbol)
  - field_reorder:    swap the balance and fee clauses
  - whitespace_bloat: double/triple spacing inside the message
  - truncation:       cut trailing marketing/reference tail (SMS length limit)
  - tx_id_label:      'Transaction ID:' → 'Trn ID:'
  - promo_injection:  insert a new marketing phrase mid-message

Random character mutations are deliberately excluded — they're noise, not a
real threat. The mutations above are the real threat.
"""
import json
import re
from pathlib import Path

import pytest

import parser as p
from parser.fuzzy import FUZZY_CONFIDENCE_CAP

CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"

_SENDER_IDS = {"mtn": "MobileMoney", "telecel": "T-CASH"}

# tx_types where amount is a critical field we expect fuzzy to always recover.
# Wallet-balance-only SMS don't have an amount, so they're excluded here.
_AMOUNT_BEARING_TX_TYPES = {
    "transfer_sent",
    "transfer_received",
    "merchant_payment",
    "bill_payment",
    "cash_withdrawal",
    "cash_in",
    "cash_out",
    "bank_transfer",
    "deposit_received",
    "payment_received",
    "airtime_purchase",
    "loan_repayment",
}


def _load_templates():
    """Yield (telco, template) for every template with a mutable example."""
    for telco, fname in [("mtn", "mtn_templates.json"), ("telecel", "telecel_templates.json")]:
        data = json.loads((CONFIG_DIR / fname).read_text(encoding="utf-8"))
        for t in data.get("templates", []):
            if not t.get("example"):
                continue
            if t.get("tx_type") not in _AMOUNT_BEARING_TX_TYPES:
                continue
            yield telco, t


# ── Drift mutations ───────────────────────────────────────────────────────────
# Each returns (mutated_sms, applied). If `applied` is False the test skips —
# the mutation's trigger wasn't present in this particular example.

def _drift_verb(sms: str) -> tuple[str, bool]:
    """Swap a transaction verb for one not in any current template."""
    for old, new in [
        (" sent to ", " moved to "),
        (" paid to ", " moved to "),
        (" transferred to ", " moved to "),
        (" received from ", " moved from "),
        (" withdrawn from ", " moved from "),
        ("Payment made for ", "Payment moved for "),
        ("Payment received for ", "Payment collected for "),
        ("Payment for ", "Charge for "),
        ("Cash Out made for ", "Cash Out moved for "),
        ("Cash In received for ", "Cash In collected for "),
        ("You have withdrawn ", "You have removed "),
    ]:
        if old in sms:
            return sms.replace(old, new, 1), True
    return sms, False


def _drift_currency(sms: str) -> tuple[str, bool]:
    """Swap 'GHS' for the cedi sign 'GH\u00a2' — a plausible format drift."""
    if "GHS" not in sms:
        return sms, False
    return sms.replace("GHS", "GH\u00a2"), True


def _drift_field_reorder(sms: str) -> tuple[str, bool]:
    """
    Move the Fee clause to appear before the balance clause.

    Real drift: telcos occasionally shuffle the order of trailing metadata
    across template revisions. Exact regex anchored on Fee-after-Balance
    should fail; fuzzy should still recover amount and balance.
    """
    # Look for a "Fee <something>. ... Balance <something>. " pattern and swap.
    fee_match = re.search(r"(Fee[^.]+?\.)\s*", sms)
    bal_match = re.search(r"((?:Current\s+Balance:|Your\s+Telecel\s+Cash\s+balance\s+is|Available\s+Balance:)[^.]+?\.)", sms)
    if not (fee_match and bal_match):
        return sms, False
    # Remove fee clause, inject it before balance clause.
    fee_text = fee_match.group(1)
    without_fee = sms[:fee_match.start()] + sms[fee_match.end():]
    bal_start = without_fee.find(bal_match.group(1))
    if bal_start == -1:
        return sms, False
    reordered = without_fee[:bal_start] + fee_text + " " + without_fee[bal_start:]
    return reordered, True


def _drift_whitespace(sms: str) -> tuple[str, bool]:
    """Inject doubled spaces after every currency marker — a realistic
    telco-side typo that exact patterns with \\s+ handle but \\s{1} don't."""
    if "GHS" not in sms:
        return sms, False
    mutated = re.sub(r"GHS\s*", "GHS  ", sms)
    mutated = re.sub(r"Balance[:\s]+", "Balance:   ", mutated)
    return mutated, True


def _drift_truncation(sms: str) -> tuple[str, bool]:
    """
    Truncate the trailing marketing/reference tail — a 160-char SMS limit
    or network truncation leaves the core money fields intact but strips the
    promo suffix that many templates use as an anchor.
    """
    # Cut right after the balance clause — keeps amount + balance, drops tail.
    for marker in [
        "Your Telecel Cash balance is GHS",
        "Your Telecel Cash balance is GH\u00a2",
        "Current Balance: GHS",
        "Available Balance: GHS",
    ]:
        idx = sms.find(marker)
        if idx == -1:
            continue
        # Keep marker + next ~20 chars (the balance amount), drop everything after.
        end = idx + len(marker) + 20
        # Round to nearest period to keep SMS well-formed.
        period = sms.find(".", end - 5)
        if period != -1 and period < len(sms) - 1:
            return sms[:period + 1], True
    return sms, False


def _drift_tx_id_label(sms: str) -> tuple[str, bool]:
    """Abbreviate the tx_id label so specific tx_id patterns miss."""
    for old, new in [
        ("Transaction ID:", "Trn ID:"),
        ("Transaction Id:", "Trn ID:"),
        ("Financial Transaction Id:", "Fin Trn ID:"),
    ]:
        if old in sms:
            return sms.replace(old, new, 1), True
    return sms, False


def _drift_inject_promo(sms: str) -> tuple[str, bool]:
    """Inject a never-before-seen marketing phrase mid-SMS."""
    injected = " NEW! Earn rewards at telcoplus.example. "
    if "Reference" in sms:
        return sms.replace("Reference", injected + "Reference", 1), True
    return sms + injected, True


_MUTATIONS = [
    ("verb_swap",        _drift_verb),
    ("currency_drift",   _drift_currency),
    ("field_reorder",    _drift_field_reorder),
    ("whitespace_bloat", _drift_whitespace),
    ("truncation",       _drift_truncation),
    ("tx_id_label",      _drift_tx_id_label),
    ("promo_injection",  _drift_inject_promo),
]


# ── Assertion helpers ─────────────────────────────────────────────────────────

def _ground_truth(sms: str, telco: str):
    """Parse the clean example to capture expected (amount, tx_type, balance)."""
    r = p.parse(sms, sender_id=_SENDER_IDS[telco])
    return r.amount, r.tx_type, r.balance


def _diagnostic(mutation_name: str, template_id: str, mutated: str, result) -> str:
    """Verbose failure message — tells you exactly what broke where."""
    snippet = mutated if len(mutated) <= 160 else mutated[:157] + "..."
    return (
        f"\n  mutation:     {mutation_name}"
        f"\n  template:     {template_id}"
        f"\n  match_mode:   {result.match_mode}"
        f"\n  template_id:  {result.template_id}"
        f"\n  amount:       {result.amount}"
        f"\n  tx_type:      {result.tx_type}"
        f"\n  balance:      {result.balance}"
        f"\n  confidence:   {result.confidence}"
        f"\n  mutated_sms:  {snippet}"
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

_TEMPLATE_CASES = list(_load_templates())


def _case_id(case):
    telco, template = case
    return f"{telco}:{template['id']}"


@pytest.mark.parametrize(
    "telco,template",
    _TEMPLATE_CASES,
    ids=[_case_id(c) for c in _TEMPLATE_CASES],
)
@pytest.mark.parametrize(
    "mutation_name,mutate",
    _MUTATIONS,
    ids=[m[0] for m in _MUTATIONS],
)
def test_drift_preserves_downstream_fields(mutation_name, mutate, telco, template):
    """
    After a realistic drift mutation, the parser must preserve the fields the
    Financial Health Index actually consumes: amount, tx_type, telco. A wrong
    tx_type corrupts savings-rate and income-stability sub-scores; a missing
    amount silently drops the transaction.
    """
    clean = template["example"]
    expected_amount, expected_tx_type, _ = _ground_truth(clean, telco)
    if expected_amount is None:
        pytest.skip(f"clean example has no recoverable amount for {template['id']}")

    mutated, applied = mutate(clean)
    if not applied:
        pytest.skip(f"mutation {mutation_name} not applicable to {template['id']}")

    result = p.parse(mutated, sender_id=_SENDER_IDS[telco])
    diag = _diagnostic(mutation_name, template["id"], mutated, result)

    assert result.telco == telco, f"telco lost under drift{diag}"
    assert result.match_mode in {"exact", "fuzzy"}, f"drift caused silent drop{diag}"
    assert result.amount == pytest.approx(expected_amount), f"amount changed under drift{diag}"
    assert result.tx_type == expected_tx_type, f"tx_type misclassified under drift{diag}"
    assert 0.0 < result.confidence <= 1.0, f"confidence out of range{diag}"

    if result.match_mode == "fuzzy":
        assert result.confidence <= FUZZY_CONFIDENCE_CAP, (
            f"fuzzy confidence exceeds cap {FUZZY_CONFIDENCE_CAP}{diag}"
        )


@pytest.mark.parametrize(
    "telco,template",
    _TEMPLATE_CASES,
    ids=[_case_id(c) for c in _TEMPLATE_CASES],
)
def test_drift_preserves_balance_when_present(telco, template):
    """
    When the clean example carries a balance, verb-swap drift must preserve
    it. Balance is the Financial Health Index's single most-consumed field.
    """
    clean = template["example"]
    _, _, expected_balance = _ground_truth(clean, telco)
    if expected_balance is None:
        pytest.skip(f"clean example has no balance for {template['id']}")

    mutated, applied = _drift_verb(clean)
    if not applied:
        pytest.skip("verb swap not applicable")

    result = p.parse(mutated, sender_id=_SENDER_IDS[telco])
    diag = _diagnostic("verb_swap", template["id"], mutated, result)
    assert result.balance == pytest.approx(expected_balance), (
        f"balance lost under verb-swap drift{diag}"
    )


def test_drift_promo_injection_never_silently_returns_none():
    """
    Universal smoke test: every amount-bearing template, under promo-injection
    drift, must remain classifiable. A 'none' verdict here means the FHI loses
    this row entirely.
    """
    failures = []
    for telco, template in _TEMPLATE_CASES:
        mutated, applied = _drift_inject_promo(template["example"])
        if not applied:
            continue
        result = p.parse(mutated, sender_id=_SENDER_IDS[telco])
        if result.match_mode == "none":
            failures.append(f"{telco}:{template['id']}")
    assert not failures, f"drift caused silent drop on: {failures}"

"""
Corpus-driven accuracy tests against the synthetic SMS corpus.
This file runs on CI (synthetic corpus is committed to the repo).
Target: 95%+ of rows parse correctly.
"""
import csv
import pytest
from helpers import SYNTHETIC_CORPUS_PATH, normalize_tx_type
import parser as p

# Canonical sender_ids per telco — mirrors real SMS metadata.
# In production, sender_id is always available from the handset.
_SENDER_IDS: dict[str, str] = {
    "mtn": "MobileMoney",
    "telecel": "T-CASH",
}


def load_synthetic_corpus():
    with open(SYNTHETIC_CORPUS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


_ROWS = load_synthetic_corpus()


def _row_id(row):
    return (row.get("tx_id") or row["raw_sms"][:50]).replace(",", " ")


@pytest.mark.parametrize("row", _ROWS, ids=_row_id)
def test_synthetic_corpus_row(row):
    sender_id = _SENDER_IDS.get(row["telco"])
    result = p.parse(row["raw_sms"], sender_id=sender_id)

    assert result.telco == row["telco"], (
        f"telco mismatch: got {result.telco!r}, expected {row['telco']!r}\n"
        f"SMS: {row['raw_sms'][:100]}"
    )
    assert result.tx_type == normalize_tx_type(row["tx_type"]), (
        f"tx_type mismatch: got {result.tx_type!r}, expected {row['tx_type']!r} "
        f"(template: {result.template_id})\n"
        f"SMS: {row['raw_sms'][:100]}"
    )
    assert result.confidence >= 0.8, (
        f"low confidence {result.confidence} (template: {result.template_id})\n"
        f"SMS: {row['raw_sms'][:100]}"
    )

    if row.get("amount"):
        try:
            expected = float(str(row["amount"]).replace(",", ""))
            assert result.amount == pytest.approx(expected, abs=0.01)
        except ValueError:
            pass

    if row.get("balance") and "[redacted]" not in str(row["balance"]):
        try:
            expected_balance = float(str(row["balance"]).replace(",", ""))
            assert result.balance == pytest.approx(expected_balance, abs=0.01)
        except ValueError:
            pass


def test_synthetic_corpus_overall_accuracy():
    """Guard: at least 95% of the synthetic corpus must parse correctly."""
    passed = 0
    total = len(_ROWS)

    for row in _ROWS:
        sender_id = _SENDER_IDS.get(row["telco"])
        result = p.parse(row["raw_sms"], sender_id=sender_id)
        if (
            result.telco == row["telco"]
            and result.tx_type == normalize_tx_type(row["tx_type"])
            and result.confidence >= 0.8
        ):
            passed += 1

    accuracy = passed / total
    assert accuracy >= 0.95, (
        f"Corpus accuracy {accuracy:.1%} is below the 95% threshold "
        f"({passed}/{total} rows passed)"
    )

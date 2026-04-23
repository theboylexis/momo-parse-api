"""
Corpus-driven accuracy tests against the real annotated SMS corpus.
Skipped automatically if corpus/real_sms_corpus.csv is not present (gitignored).
Run locally: pytest tests/test_corpus_real.py -v
"""
import csv
import re
import pytest
from helpers import REAL_CORPUS_PATH, normalize_tx_type
import parser as p
from parser.pipeline import _is_failure_notice

_SENDER_IDS: dict[str, str] = {
    "mtn": "MobileMoney",
    "telecel": "T-CASH",
}


def load_real_corpus():
    if not REAL_CORPUS_PATH.exists():
        return []
    with open(REAL_CORPUS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


_ROWS = load_real_corpus()

if not _ROWS:
    pytest.skip("real_sms_corpus.csv not found — skipping real corpus tests", allow_module_level=True)


# Token shapes the import pipeline substitutes for PII (see
# scripts/import_sms_xml.py). When these appear in ``raw_sms`` the
# telco-specific template regexes (which expect digit-only phones and
# capitalized names) can no longer match exactly, so fuzzy fallback
# takes over with low confidence. The parser itself is not regressed
# on real SMS; the stored corpus row just isn't parseable as-is.
_HASH_TOKENS = re.compile(r"\bname_[0-9a-f]{8,}|ph_[0-9a-f]{8,}\b")


def _row_id(row):
    return row.get("tx_id") or row["raw_sms"][:50].replace(",", " ")


@pytest.mark.parametrize("row", _ROWS, ids=_row_id)
def test_real_corpus_row(row):
    if "[redacted]" in row["raw_sms"]:
        pytest.skip("SMS text contains [redacted] — cannot parse")
    if _HASH_TOKENS.search(row["raw_sms"]):
        pytest.skip("SMS text contains PII hash tokens — template regexes expect raw digits/caps")
    if _is_failure_notice(row["raw_sms"]):
        # Early imports stored failed-transaction notices (daily-limit, voucher
        # expiry) as real transactions; the parser now correctly rejects them.
        # The stale rows remain in the corpus until the next import rewrite.
        pytest.skip("failure/reversal notice — parser correctly yields match_mode=none")
    sender_id = _SENDER_IDS.get(row["telco"])
    result = p.parse(row["raw_sms"], sender_id=sender_id)

    assert result.telco == row["telco"], (
        f"telco mismatch: got {result.telco!r}, expected {row['telco']!r}"
    )
    assert result.tx_type == normalize_tx_type(row["tx_type"]), (
        f"tx_type mismatch: got {result.tx_type!r}, expected {row['tx_type']!r} "
        f"(template: {result.template_id})"
    )
    assert result.confidence >= 0.8, (
        f"low confidence {result.confidence} for template {result.template_id}"
    )

    if row["amount"]:
        assert result.amount == pytest.approx(float(row["amount"]), abs=0.01), (
            f"amount mismatch: got {result.amount}, expected {row['amount']}"
        )

    balance_str = row.get("balance", "")
    if balance_str and "[redacted]" not in balance_str:
        try:
            expected_balance = float(balance_str)
            assert result.balance == pytest.approx(expected_balance, abs=0.01)
        except ValueError:
            pass

    if row.get("fee"):
        try:
            assert result.fee == pytest.approx(float(row["fee"]), abs=0.01)
        except ValueError:
            pass

    if row.get("tx_id"):
        assert result.tx_id == row["tx_id"]

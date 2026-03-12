"""Shared helpers for the MomoParse test suite."""
from pathlib import Path

REAL_CORPUS_PATH = Path(__file__).parent.parent / "corpus" / "real_sms_corpus.csv"
SYNTHETIC_CORPUS_PATH = Path(__file__).parent.parent / "corpus" / "synthetic_sms_corpus.csv"

# Parser outputs bill_payment for mtn_service_payment, which also covers MTN data bundles.
TX_TYPE_ALIASES: dict[str, str] = {
    "bundle_purchase": "bill_payment",
}


def normalize_tx_type(tx_type: str) -> str:
    return TX_TYPE_ALIASES.get(tx_type, tx_type)

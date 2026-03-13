"""
MomoParse Categorization Engine — public interface.

Usage:
    from categorizer.pipeline import categorize

    slug, confidence = categorize(
        tx_type="transfer_sent",
        amount=250.0,
        reference="rent payment",
        counterparty_name="KOFI MENSAH",
    )
    # → ("rent", 0.87)
"""
from categorizer.pipeline import categorize
from categorizer.taxonomy import CATEGORIES, BY_SLUG, SLUGS, get

__all__ = ["categorize", "CATEGORIES", "BY_SLUG", "SLUGS", "get"]

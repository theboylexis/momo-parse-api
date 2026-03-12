"""
Stage 2 — Template Matching
Scores each template in the telco's registry against the SMS and returns the best match.
"""
import re
from typing import Optional

from .config_loader import load_all_templates

# Fields that MUST be captured for a match to be considered high-confidence
_CRITICAL_FIELDS: dict[str, list[str]] = {
    "transfer_sent":     ["amount", "counterparty_name", "balance"],
    "transfer_received": ["amount", "counterparty_name", "balance"],
    "merchant_payment":  ["amount", "counterparty_name", "balance"],
    "bill_payment":      ["amount", "counterparty_name", "balance"],
    "airtime_purchase":  ["amount", "balance"],
    "airtime_received":  ["amount", "counterparty_name"],
    "cash_withdrawal":   ["amount", "counterparty_name", "balance"],
    "cash_in":           ["amount", "counterparty_name", "balance"],
    "cash_out":          ["amount", "counterparty_name", "balance"],
    "bank_transfer":     ["amount", "counterparty_name", "balance"],
    "deposit_received":  ["amount", "counterparty_name", "balance"],
    "loan_repayment":    ["amount", "balance"],
    "interest_received": ["amount", "balance"],
    "wallet_balance":    ["balance"],
}


class TemplateMatcher:
    def __init__(self):
        self._configs = load_all_templates()

    def match(
        self, telco: str, sms_text: str
    ) -> tuple[Optional[dict], Optional[re.Match], float]:
        """
        Returns (template, match_object, confidence).

        Confidence scoring:
          1.0 — full regex match + all critical fields captured
          0.9 — full regex match but some critical fields missing
          0.8 — full regex match, heuristic fill-in needed
          0.0 — no template matched
        """
        if telco not in self._configs:
            return None, None, 0.0

        templates = self._configs[telco].get("templates", [])
        best_template = None
        best_match = None
        best_confidence = 0.0

        for template in templates:
            pattern_str = template.get("pattern", "")
            try:
                m = re.search(pattern_str, sms_text, re.DOTALL)
            except re.error:
                continue

            if not m:
                continue

            confidence = self._score(template, m)
            if confidence > best_confidence:
                best_confidence = confidence
                best_template = template
                best_match = m

        return best_template, best_match, best_confidence

    def _score(self, template: dict, match: re.Match) -> float:
        """Score a successful regex match based on critical field capture rate."""
        tx_type = template.get("tx_type", "")
        critical = _CRITICAL_FIELDS.get(tx_type, [])

        groups = match.groupdict()
        captured_critical = sum(
            1 for f in critical if groups.get(f) is not None
        )

        if not critical:
            return 1.0
        if captured_critical == len(critical):
            return 1.0
        if captured_critical >= len(critical) - 1:
            return 0.9
        return 0.8

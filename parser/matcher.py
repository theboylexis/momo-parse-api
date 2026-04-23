"""
Stage 2 — Template Matching
Scores each template in the telco's registry against the SMS and returns the best match.

Scoring is a continuous weighted ratio of critical fields captured. A full regex
match with every critical field present scores 1.0. If no template matches fully,
a fuzzy fallback picks the nearest template by token overlap and extracts whatever
fields it can with a capped confidence.
"""
import re
from typing import Optional

from .config_loader import load_all_templates
from .fuzzy import fuzzy_match, FUZZY_CONFIDENCE_CAP
from .telemetry import emit_fuzzy_fallback

# Critical fields per tx_type, each with a relative importance weight.
# A transaction is useless without amount; counterparty and balance are needed
# for categorization and index computation; date/tx_id are metadata.
_CRITICAL_FIELDS: dict[str, dict[str, int]] = {
    "transfer_sent":     {"amount": 3, "counterparty_name": 2, "balance": 2},
    "transfer_received": {"amount": 3, "counterparty_name": 2, "balance": 2},
    "merchant_payment":  {"amount": 3, "counterparty_name": 2, "balance": 2},
    "bill_payment":      {"amount": 3, "counterparty_name": 2, "balance": 2},
    "airtime_purchase":  {"amount": 3, "balance": 2},
    "airtime_received":  {"amount": 3, "counterparty_name": 2},
    "cash_withdrawal":   {"amount": 3, "counterparty_name": 2, "balance": 2},
    "cash_in":           {"amount": 3, "counterparty_name": 2, "balance": 2},
    "cash_out":          {"amount": 3, "counterparty_name": 2, "balance": 2},
    "bank_transfer":     {"amount": 3, "counterparty_name": 2, "balance": 2},
    "deposit_received":  {"amount": 3, "counterparty_name": 2, "balance": 2},
    "loan_repayment":    {"amount": 3, "balance": 2},
    "interest_received": {"amount": 3, "balance": 2},
    "wallet_balance":    {"balance": 2},
    "payment_received":  {"amount": 3, "counterparty_name": 2, "balance": 2},
    "bundle_purchase":   {"amount": 3, "balance": 2},  # telecel-specific; MTN bundles are bill_payment
}


class TemplateMatcher:
    def __init__(self):
        self._configs = load_all_templates()

    def match(
        self, telco: str, sms_text: str
    ) -> tuple[Optional[dict], dict, float, str]:
        """
        Returns (template, groups, confidence, match_mode).

        match_mode:
          "exact" — a template's full regex matched
          "fuzzy" — regex failed; nearest template picked by token overlap
          "none"  — no template identifiable

        confidence is a continuous weighted ratio of critical fields captured.
        Fuzzy results are capped at FUZZY_CONFIDENCE_CAP so they always rank
        below a clean exact match.
        """
        if telco not in self._configs:
            return None, {}, 0.0, "none"

        templates = self._configs[telco].get("templates", [])

        best_template, best_groups, best_conf = self._try_exact(templates, sms_text)
        if best_template is not None:
            return best_template, best_groups, best_conf, "exact"

        # Fuzzy matching is Jaccard-based on raw tokens — which means a
        # "Your payment of X to Y has been completed" SMS for a generic
        # merchant can rank an airtime template above a merchant template
        # because the boilerplate tokens dominate. To keep fuzzy picks
        # semantically honest, require that tx_types with a distinctive
        # keyword signal only match when that keyword is actually in the
        # SMS (airtime, bundle, withdrawal, deposit, etc.).
        fuzzy_candidates = [
            t for t in templates
            if self._tx_type_signal_present(t.get("tx_type", ""), sms_text)
        ]
        f_template, f_groups, similarity = fuzzy_match(sms_text, fuzzy_candidates)
        if f_template is None:
            return None, {}, 0.0, "none"

        field_score = self._field_capture_score(f_template, f_groups)
        confidence = round(
            min(FUZZY_CONFIDENCE_CAP, similarity) * max(field_score, 0.1), 2
        )

        captured, missing = self._critical_field_split(f_template, f_groups)
        emit_fuzzy_fallback(
            telco=telco,
            template_id=f_template.get("id", "unknown"),
            similarity=similarity,
            confidence=confidence,
            captured_fields=captured,
            missing_critical_fields=missing,
            sms_text=sms_text,
        )
        return f_template, f_groups, confidence, "fuzzy"

    def _try_exact(
        self, templates: list[dict], sms_text: str
    ) -> tuple[Optional[dict], dict, float]:
        best_template = None
        best_groups: dict = {}
        best_confidence = 0.0

        for template in templates:
            pattern_str = template.get("pattern", "")
            try:
                m = re.search(pattern_str, sms_text, re.DOTALL)
            except re.error:
                continue
            if not m:
                continue

            groups = {k: v for k, v in m.groupdict().items() if v is not None}
            confidence = self._field_capture_score(template, groups)
            if confidence > best_confidence:
                best_confidence = confidence
                best_template = template
                best_groups = groups

        return best_template, best_groups, round(best_confidence, 2)

    def _field_capture_score(self, template: dict, groups: dict) -> float:
        """
        Weighted ratio of critical fields the template resolves for this tx_type.
        A field counts as captured if the template rule is a literal (always
        resolves) or a named group that is present in ``groups``. Templates
        explicitly set a field to ``null`` to declare it structurally absent
        (e.g. MTN's money-transfer-deposit SMS carries no balance) — such
        fields drop out of the score's denominator rather than counting as a
        miss. Returns 1.0 when all applicable critical fields resolve, 0.0
        when none do.
        """
        tx_type = template.get("tx_type", "")
        weights = _CRITICAL_FIELDS.get(tx_type, {})
        if not weights:
            return 1.0

        field_rules = template.get("fields", {})
        applicable = {f: w for f, w in weights.items() if field_rules.get(f) is not None}
        if not applicable:
            return 1.0

        total = sum(applicable.values())
        captured = sum(
            w for f, w in applicable.items()
            if self._field_resolves(field_rules[f], groups)
        )
        return captured / total if total else 1.0

    def _critical_field_split(
        self, template: dict, groups: dict
    ) -> tuple[list[str], list[str]]:
        """Partition this template's critical fields into (captured, missing)."""
        weights = _CRITICAL_FIELDS.get(template.get("tx_type", ""), {})
        field_rules = template.get("fields", {})
        captured: list[str] = []
        missing: list[str] = []
        for field in weights:
            if self._field_resolves(field_rules.get(field), groups):
                captured.append(field)
            else:
                missing.append(field)
        return captured, missing

    @staticmethod
    def _field_resolves(rule, groups: dict) -> bool:
        if isinstance(rule, str) and rule.startswith("literal:"):
            return True
        if isinstance(rule, str) and rule.startswith("group:"):
            return groups.get(rule[6:]) is not None
        return False

    # Keyword signals required in the SMS for tx_types that would
    # otherwise cross-contaminate via fuzzy token overlap. An "airtime"
    # template picked by Jaccard similarity for a generic merchant-payment
    # SMS is how airtime totals ended up inflated by ~GHS 880k in the
    # real-data demo. Only *product nouns* are gated here — not verbs —
    # because the drift benchmark mutates verbs (``withdrawn → removed``)
    # and requires fuzzy matching to survive those swaps. Product nouns
    # (airtime, bundle, loan, interest) are stable brand/product terms
    # telcos do not routinely rewrite, so requiring them does not defeat
    # drift tolerance.
    _TX_TYPE_SIGNALS: dict[str, tuple[str, ...]] = {
        "airtime_purchase":  ("airtime",),
        "airtime_received":  ("airtime",),
        "bundle_purchase":   ("bundle",),
        "loan_repayment":    ("loan",),
        "loan_disbursement": ("loan",),
        "interest_received": ("interest",),
    }

    @classmethod
    def _tx_type_signal_present(cls, tx_type: str, sms_text: str) -> bool:
        """True if the SMS contains at least one signal word for this tx_type.
        Returns True for tx_types without a required signal (the default)."""
        signals = cls._TX_TYPE_SIGNALS.get(tx_type)
        if not signals:
            return True
        lower = sms_text.lower()
        return any(s in lower for s in signals)

"""
Stage 3 — Field Extraction
Applies field rules from the matched template to pull structured data from the regex match.
"""
import re
from typing import Optional

from .normalizers import normalize_amount, normalize_phone, normalize_name

_AMOUNT_FIELDS = {"amount", "balance", "fee", "e_levy"}
_PHONE_FIELDS = {"counterparty_phone"}
_NAME_FIELDS = {"counterparty_name"}


class FieldExtractor:
    def extract(self, template: dict, match: re.Match) -> dict:
        """
        Apply the template's field rules to the regex match.

        Rule types:
          "group:<name>"   — use the named capture group from the regex
          "literal:<val>"  — hard-code this value regardless of SMS content
          null             — field not present in this template; return None
        """
        groups = match.groupdict()
        field_rules: dict = template.get("fields", {})
        result: dict = {}

        for field_name, rule in field_rules.items():
            if rule is None:
                result[field_name] = None
            elif isinstance(rule, str) and rule.startswith("group:"):
                group_key = rule[6:]
                result[field_name] = groups.get(group_key)
            elif isinstance(rule, str) and rule.startswith("literal:"):
                result[field_name] = rule[8:]
            else:
                result[field_name] = None

        # Normalize values
        for f in _AMOUNT_FIELDS:
            if result.get(f) is not None:
                result[f] = normalize_amount(result[f])

        for f in _PHONE_FIELDS:
            if result.get(f) is not None:
                result[f] = normalize_phone(result[f])

        for f in _NAME_FIELDS:
            if result.get(f) is not None:
                result[f] = normalize_name(result[f])

        return result

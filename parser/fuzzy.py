"""
Fuzzy fallback — runs when no template's full regex matches.

Picks the nearest template by token overlap with the template's example SMS,
then extracts whatever fields it can using telco-neutral field regexes.
Returns a partial groups dict with match_mode="fuzzy" and a capped confidence,
so downstream indexes receive best-effort data instead of a silent drop.
"""
import re
from typing import Optional

# Confidence cap for any fuzzy result — always below a clean full-regex match.
FUZZY_CONFIDENCE_CAP = 0.6

# Minimum Jaccard similarity required to select a template in fuzzy mode.
# Below this, the SMS is genuinely unrelated and we give up.
FUZZY_TEMPLATE_THRESHOLD = 0.2

# Telco-neutral field regexes — ordered most-specific first within each field.
# Used only when the template's own pattern failed; these cover common wording
# used across MTN and Telecel formats.
_CCY = r"(?:GHS|GH\xa2|GH\u00a2|\u20b5)"  # GHS | GH¢ | ₵

_FUZZY_FIELD_PATTERNS: dict[str, list[str]] = {
    "amount": [
        rf"(?:for|to|of)\s+{_CCY}\s*(?P<v>[\d,]+\.?\d*)",
        rf"(?:withdrawn|deposited|received|sent|paid|transferred)\s+{_CCY}\s*(?P<v>[\d,]+\.?\d*)",
        rf"{_CCY}\s*(?P<v>[\d,]+\.?\d*)\s+(?:sent|received|paid|transferred|withdrawn|from|to)",
        # Last-resort: first currency amount in the text, excluding a leading "Fee ".
        # Only reached when the more specific patterns above all miss.
        rf"(?<![Ff]ee\s){_CCY}\s*(?P<v>[\d,]+\.?\d*)",
    ],
    "balance": [
        rf"(?:[Cc]urrent|[Nn]ew)(?:\s+\w+){{0,3}}\s+[Bb]alance[:\s]*(?:is\s+)?{_CCY}\s*(?P<v>[\d,]+\.?\d*)",
        rf"[Cc]ash\s+balance\s+(?:is|:)\s*{_CCY}\s*(?P<v>[\d,]+\.?\d*)",
        rf"[Bb]alance[:\s]+(?:is\s+)?{_CCY}\s*(?P<v>[\d,]+\.?\d*)",
    ],
    "tx_id": [
        r"(?:[Ff]inancial\s+[Tt]ransaction\s+Id|[Tt]ransaction\s+(?:ID|Id))[:\s]+(?P<v>\d+)",
        r"^(?P<v>\d{14,20})\s+Confirmed",
    ],
    "date": [
        r"(?P<v>\d{4}-\d{2}-\d{2})",
    ],
    "time": [
        r"(?P<v>\d{2}:\d{2}:\d{2})",
    ],
    "counterparty_name": [
        r"(?:from|to)\s+(?P<v>[A-Z][A-Z][A-Z\s'.\-&]+?)(?=\s+on\s|\s+Current|\.\s|,\s|\s+\d{4}-)",
    ],
    "fee": [
        r"[Ff]ee\s+(?:charged|was)[:\s]*GHS\s*(?P<v>[\d.]+)",
        r"charged\s+GHS\s*(?P<v>[\d.]+)",
    ],
    "reference": [
        r"Reference:\s*(?P<v>.+?)(?:\.\s|$)",
        r"Ref:\s*(?P<v>.+?)(?:\.\s|$)",
    ],
    "counterparty_phone": [
        r"(?P<v>233\d{9}|0\d{9})",
    ],
}

_TOKEN_RE = re.compile(r"[A-Za-z]{3,}")


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _extract_fields(sms_text: str, template: dict) -> dict:
    """Pull fields using generic regexes, but only for fields this template declares."""
    declared = set(template.get("fields", {}).keys())
    groups: dict = {}
    for field, patterns in _FUZZY_FIELD_PATTERNS.items():
        if field not in declared:
            continue
        for pat in patterns:
            m = re.search(pat, sms_text)
            if m:
                groups[field] = m.group("v").strip()
                break
    return groups


def fuzzy_match(
    sms_text: str, templates: list[dict]
) -> tuple[Optional[dict], dict, float]:
    """
    Pick the best template by token overlap, then extract what fields we can.

    Returns (template, groups_dict, similarity). Caller applies confidence cap
    and critical-field weighting. Returns (None, {}, 0.0) if no template crosses
    the similarity threshold.
    """
    sms_tokens = _tokenize(sms_text)
    if not sms_tokens:
        return None, {}, 0.0

    best_template = None
    best_sim = 0.0
    for t in templates:
        example = t.get("example", "")
        if not example:
            continue
        sim = _jaccard(sms_tokens, _tokenize(example))
        if sim > best_sim:
            best_sim = sim
            best_template = t

    if best_template is None or best_sim < FUZZY_TEMPLATE_THRESHOLD:
        return None, {}, 0.0

    groups = _extract_fields(sms_text, best_template)
    return best_template, groups, best_sim

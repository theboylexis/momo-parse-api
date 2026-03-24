"""
Stage 1 — Telco Detection
Identifies which telco sent the SMS using sender ID first, then content patterns.
"""
import re
from typing import Optional

from .config_loader import get_sender_map

# Content-based fallback patterns — ordered most-specific first
_CONTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"Telecel Cash|Sendi k3k3|TelecelPlayGhana|T-CASH", re.IGNORECASE), "telecel"),
    (re.compile(r"MTN Mobile Money|MobileMoney|downloadMyMoMo|MTN MoMo", re.IGNORECASE), "mtn"),
    # Brandless MTN templates: "Payment received/made ... Transaction ID ... TRANSACTION FEE"
    # These lack any MTN branding but the field layout is unique to MTN MoMo
    (re.compile(
        r"Payment (?:received|made) for GHS .+?"
        r"Current Balance: GHS .+?"
        r"Available Balance: GHS .+?"
        r"Transaction ID: \d+\.\s*(?:TRANSACTION FEE|Fee charged)",
    ), "mtn"),
    # Cash Out / Cash In — MTN-specific openers
    (re.compile(r"Cash (?:Out made|In received) for GHS", re.IGNORECASE), "mtn"),
]


class TelcoDetector:
    def __init__(self):
        self._sender_map = get_sender_map()

    def detect(self, sms_text: str, sender_id: Optional[str] = None) -> tuple[str, float]:
        """
        Returns (telco, confidence).
        - 1.0: matched via sender_id (authoritative)
        - 0.9: matched via content pattern
        - 0.0: unrecognized
        """
        if sender_id and sender_id in self._sender_map:
            return self._sender_map[sender_id], 1.0

        for pattern, telco in _CONTENT_PATTERNS:
            if pattern.search(sms_text):
                return telco, 0.9

        return "unknown", 0.0

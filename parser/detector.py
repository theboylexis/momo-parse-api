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
    (re.compile(r"AirtelTigo Money", re.IGNORECASE), "airteigo"),
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

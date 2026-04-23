"""
MoMo Parser — 3-stage pipeline orchestrator.

  Stage 1 (TelcoDetector)  → which telco sent this SMS?
  Stage 2 (TemplateMatcher) → which template best describes it?
  Stage 3 (FieldExtractor)  → extract structured fields from the match.
"""
import re
from typing import Optional

from .models import ParseResult
from .detector import TelcoDetector
from .matcher import TemplateMatcher
from .extractor import FieldExtractor


# Two classes of SMS that look transaction-shaped (contain amounts, tx ids,
# counterparty-like phrases) but should not be counted. Both return
# match_mode=none so downstream aggregation doesn't inflate totals.
#
# FAILURES — the transaction did NOT execute (daily-limit, insufficient
#   funds, voucher expired, "has failed at..."). Counting them inflates
#   category totals.
# NOTIFICATIONS — the SMS is a second confirmation for a transaction that
#   is already fully captured by a paired SMS with the same tx_id. For
#   example MTN sends a low-info "Deposit made to your bank account
#   number: ****XXXX..." alongside the rich "Your payment of GHS X to
#   <bank> has been completed..." SMS. Accepting the low-info one (which
#   arrives first) silently dedupes the real transaction out.
_FAILURE_MARKERS = re.compile(
    r"(?:"
    r"has\s+failed\s+at|"
    r"failed\s+to\s+(?:send|receive|complete|debit|credit)|"
    r"exceeded\s+your\s+daily\s+transaction\s+limit|"
    r"transaction\s+(?:declined|rejected|reversed|failed|unsuccessful)|"
    r"could\s+not\s+be\s+(?:completed|processed)|"
    r"insufficient\s+(?:funds|balance)|"
    r"expired\s+and\s+has\s+been\s+returned"
    r")",
    re.IGNORECASE,
)

_NOTIFICATION_ONLY = re.compile(
    r"^Deposit\s+made\s+to\s+your\s+bank\s+account\s+number",
    re.IGNORECASE,
)


def _is_failure_notice(sms_text: str) -> bool:
    """True if the SMS describes a transaction that did not execute, or is a
    low-info duplicate notification whose paired SMS carries the real data."""
    return bool(
        _FAILURE_MARKERS.search(sms_text) or _NOTIFICATION_ONLY.search(sms_text)
    )


class MoMoParser:
    def __init__(self):
        self.detector = TelcoDetector()
        self.matcher = TemplateMatcher()
        self.extractor = FieldExtractor()

    def parse(self, sms_text: str, sender_id: Optional[str] = None) -> ParseResult:
        """
        Parse a raw MoMo SMS and return a structured ParseResult.

        Args:
            sms_text:  Raw SMS body text.
            sender_id: Optional sender short-code / name from the SMS metadata
                       (e.g. "MobileMoney", "T-CASH"). Improves telco detection
                       accuracy when available.

        Returns:
            ParseResult with all extracted fields and a confidence score.
        """
        if _is_failure_notice(sms_text):
            return ParseResult(
                raw_sms=sms_text,
                telco="unknown",
                tx_type="unknown",
                template_id=None,
                confidence=0.0,
                match_mode="none",
                amount=None,
            )

        telco, telco_conf = self.detector.detect(sms_text, sender_id)

        if telco == "unknown":
            return ParseResult(
                raw_sms=sms_text,
                telco="unknown",
                tx_type="unknown",
                template_id=None,
                confidence=0.0,
                match_mode="none",
                amount=None,
            )

        template, groups, match_conf, match_mode = self.matcher.match(telco, sms_text)

        if template is None:
            return ParseResult(
                raw_sms=sms_text,
                telco=telco,
                tx_type="unknown",
                template_id=None,
                confidence=round(0.5 * telco_conf, 2),
                match_mode="none",
                amount=None,
            )

        fields = self.extractor.extract(template, groups)

        # Chain is only as strong as its weakest link.
        confidence = round(min(telco_conf, match_conf), 2)

        return ParseResult(
            raw_sms=sms_text,
            telco=telco,
            tx_type=template["tx_type"],
            template_id=template["id"],
            confidence=confidence,
            match_mode=match_mode,
            amount=fields.get("amount"),
            balance=fields.get("balance"),
            fee=fields.get("fee") or 0.0,
            counterparty_name=fields.get("counterparty_name"),
            counterparty_phone=fields.get("counterparty_phone"),
            tx_id=fields.get("tx_id"),
            reference=fields.get("reference"),
            date=fields.get("date"),
            time=fields.get("time"),
        )

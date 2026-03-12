"""
MoMo Parser — 3-stage pipeline orchestrator.

  Stage 1 (TelcoDetector)  → which telco sent this SMS?
  Stage 2 (TemplateMatcher) → which template best describes it?
  Stage 3 (FieldExtractor)  → extract structured fields from the match.
"""
from typing import Optional

from .models import ParseResult
from .detector import TelcoDetector
from .matcher import TemplateMatcher
from .extractor import FieldExtractor


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
        # ── Stage 1: Telco Detection ─────────────────────────────────────────
        telco, telco_conf = self.detector.detect(sms_text, sender_id)

        if telco == "unknown":
            return ParseResult(
                raw_sms=sms_text,
                telco="unknown",
                tx_type="unknown",
                template_id=None,
                confidence=0.0,
                amount=None,
            )

        # ── Stage 2: Template Matching ───────────────────────────────────────
        template, match_obj, match_conf = self.matcher.match(telco, sms_text)

        if template is None or match_obj is None:
            # Telco identified but no template matched
            return ParseResult(
                raw_sms=sms_text,
                telco=telco,
                tx_type="unknown",
                template_id=None,
                confidence=round(0.5 * telco_conf, 2),
                amount=None,
            )

        # ── Stage 3: Field Extraction ────────────────────────────────────────
        fields = self.extractor.extract(template, match_obj)

        # Final confidence: minimum of telco and template match scores
        # (a chain is only as strong as its weakest link)
        confidence = round(min(telco_conf, match_conf), 2)

        return ParseResult(
            raw_sms=sms_text,
            telco=telco,
            tx_type=template["tx_type"],
            template_id=template["id"],
            confidence=confidence,
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

"""
Drift telemetry — emitted when the parser falls back to the fuzzy path.

Over a week of production traffic, aggregating these events reveals which
templates are drifting (same template_id showing up repeatedly in fuzzy mode
with the same missing fields). That list is the roadmap for v3 template
versions. No raw SMS content is logged — only a 16-char SHA-256 prefix for
correlation — so PII never reaches log storage.

Consumers: Railway logs / Datadog / any JSON-line ingest. The JSONFormatter
in api.logging_config promotes the `extra=` fields to top-level keys so
filters like `event="parse.fuzzy_fallback" template_id="telecel_bank_transfer_v2"`
work directly.
"""
from __future__ import annotations

import hashlib
import logging

_logger = logging.getLogger("momoparse.drift")


def emit_fuzzy_fallback(
    telco: str,
    template_id: str,
    similarity: float,
    confidence: float,
    captured_fields: list[str],
    missing_critical_fields: list[str],
    sms_text: str,
) -> None:
    """Record a single fuzzy-fallback event.

    Call once per parse() whose match_mode ends up "fuzzy". Safe to call from
    hot paths — the underlying logger is a no-op if nothing is attached.
    """
    _logger.info(
        "fuzzy_fallback",
        extra={
            "event": "parse.fuzzy_fallback",
            "telco": telco,
            "template_id": template_id,
            "similarity": round(similarity, 3),
            "confidence": confidence,
            "captured_fields": sorted(captured_fields),
            "missing_critical_fields": sorted(missing_critical_fields),
            "sms_hash": hashlib.sha256(sms_text.encode("utf-8")).hexdigest()[:16],
            "sms_length": len(sms_text),
        },
    )

"""
Structured logging configuration.

JSON output in production (APP_ENV=production), human-readable in dev.
Call setup_logging() once at app startup.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line — easy to ingest in Railway / Datadog / etc."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        # Include extra fields attached by callers
        for key in (
            # HTTP request context
            "request_id", "method", "path", "status_code", "duration_ms",
            # Drift telemetry — emitted when the parser falls back to fuzzy.
            # Aggregating these over a week of traffic shows which templates
            # need v3 versions.
            "event", "telco", "template_id", "similarity",
            "confidence", "captured_fields", "missing_critical_fields",
            "sms_hash", "sms_length",
        ):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        return json.dumps(entry)


def setup_logging() -> None:
    env = os.getenv("APP_ENV", "development")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s")
        )

    root.handlers = [handler]

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

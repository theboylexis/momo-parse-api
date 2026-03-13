"""
Pydantic request / response models for the MomoParse API.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Request models ────────────────────────────────────────────────────────────

class ParseRequest(BaseModel):
    sms_text: str = Field(..., min_length=1, description="Raw MoMo SMS text to parse")
    sender_id: Optional[str] = Field(
        None,
        max_length=50,
        description="SMS sender ID (e.g. 'MobileMoney', 'T-CASH'). Improves telco detection.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Optional caller-supplied metadata echoed back in the response.",
    )

    @field_validator("sms_text")
    @classmethod
    def sms_text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sms_text must not be blank")
        return v


class BatchParseRequest(BaseModel):
    messages: list[ParseRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Array of SMS messages to parse (max 100 per request).",
    )


# ── Response models ───────────────────────────────────────────────────────────

class CounterpartyModel(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class ParseResponse(BaseModel):
    request_id: str = Field(description="Unique ID for this parse request.")
    api_version: str = Field(default="v1")
    processing_time_ms: float = Field(description="End-to-end processing time in milliseconds.")

    # Core parse fields
    telco: str
    tx_type: str
    template_id: Optional[str] = None
    confidence: float

    amount: Optional[float] = None
    currency: str = "GHS"
    balance: Optional[float] = None
    fee: Optional[float] = None

    counterparty: CounterpartyModel
    tx_id: Optional[str] = None
    reference: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None

    # Categorization (Week 5)
    category: Optional[str] = Field(None, description="Financial category slug (e.g. 'personal_transfer_sent')")
    category_label: Optional[str] = Field(None, description="Human-readable category label")
    category_confidence: Optional[float] = Field(None, description="Categorization confidence in [0, 1]")

    metadata: Optional[dict[str, Any]] = None


class BatchParseResponse(BaseModel):
    request_id: str
    api_version: str = "v1"
    processing_time_ms: float
    count: int
    results: list[ParseResponse]


# ── Error models ──────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    error_code: str
    message: str
    documentation_url: str = "https://docs.momoparse.com/errors"


# ── Health model ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    uptime_seconds: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def new_request_id() -> str:
    return str(uuid.uuid4())


_SERVER_START = time.monotonic()


def uptime() -> float:
    return round(time.monotonic() - _SERVER_START, 2)

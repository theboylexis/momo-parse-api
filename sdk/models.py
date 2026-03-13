"""
Typed result objects returned by the SDK.
All fields mirror the API response schema exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Counterparty:
    name: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class ParseResult:
    # Envelope
    request_id: str = ""
    api_version: str = "v1"
    processing_time_ms: float = 0.0

    # Core parse fields
    telco: str = "unknown"
    tx_type: str = "unknown"
    template_id: Optional[str] = None
    confidence: float = 0.0

    # Money
    amount: Optional[float] = None
    currency: str = "GHS"
    balance: Optional[float] = None
    fee: Optional[float] = None

    # Counterparty
    counterparty: Counterparty = field(default_factory=Counterparty)

    # Identifiers / meta
    tx_id: Optional[str] = None
    reference: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "ParseResult":
        cp = data.get("counterparty") or {}
        return cls(
            request_id=data.get("request_id", ""),
            api_version=data.get("api_version", "v1"),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            telco=data.get("telco", "unknown"),
            tx_type=data.get("tx_type", "unknown"),
            template_id=data.get("template_id"),
            confidence=data.get("confidence", 0.0),
            amount=data.get("amount"),
            currency=data.get("currency", "GHS"),
            balance=data.get("balance"),
            fee=data.get("fee"),
            counterparty=Counterparty(
                name=cp.get("name"),
                phone=cp.get("phone"),
            ),
            tx_id=data.get("tx_id"),
            reference=data.get("reference"),
            date=data.get("date"),
            time=data.get("time"),
            metadata=data.get("metadata"),
        )

    def __repr__(self) -> str:
        return (
            f"ParseResult(telco={self.telco!r}, tx_type={self.tx_type!r}, "
            f"amount={self.amount}, confidence={self.confidence})"
        )


@dataclass
class BatchResult:
    request_id: str
    api_version: str
    processing_time_ms: float
    count: int
    results: list[ParseResult]

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "BatchResult":
        return cls(
            request_id=data["request_id"],
            api_version=data.get("api_version", "v1"),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            count=data.get("count", 0),
            results=[ParseResult._from_dict(r) for r in data.get("results", [])],
        )

    def __repr__(self) -> str:
        return f"BatchResult(count={self.count}, processing_time_ms={self.processing_time_ms})"
